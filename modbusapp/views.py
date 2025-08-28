import json
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
from .models import ModbusDevice, PollResult, ModbusCard, ModbusActionCard
from .modbus_client import write_coils_to_device


def list_devices(request):
    devices = list(ModbusDevice.objects.filter(enabled=True).values('id', 'name', 'host', 'port', 'unit_id'))
    return JsonResponse({'devices': devices})


def last_poll(request, device_id: int):
    try:
        device = ModbusDevice.objects.get(id=device_id)
    except ModbusDevice.DoesNotExist:
        return JsonResponse({'error': 'device not found'}, status=404)
    poll = device.polls.first()
    if not poll:
        return JsonResponse({'message': 'no data yet'})
    return JsonResponse({
        'device': device.id,
        'created_at': poll.created_at.isoformat(),
        'ok': poll.ok,
        'error': poll.error,
        'discrete_inputs': poll.discrete_inputs,
        'input_registers': poll.input_registers,
        'holding_registers': poll.holding_registers,
        'coils': poll.coils,
    })


@csrf_exempt
@require_http_methods(["POST"])
def write_coils(request, device_id: int):
    try:
        body = json.loads(request.body.decode('utf-8'))
    except Exception:
        return HttpResponseBadRequest('Invalid JSON body')
    start = int(body.get('start', 0))
    values = body.get('values', [])
    if not isinstance(values, list) or not all(isinstance(v, bool) for v in values):
        return HttpResponseBadRequest('values must be a list of booleans')
    try:
        device = ModbusDevice.objects.get(id=device_id)
    except ModbusDevice.DoesNotExist:
        return JsonResponse({'error': 'device not found'}, status=404)
    ok, err = write_coils_to_device(device, start, values)
    status = 200 if ok else 500
    return JsonResponse({'ok': ok, 'error': err}, status=status)


def dashboard(request):
    devices = ModbusDevice.objects.filter(enabled=True).prefetch_related('cards', 'actions').order_by('id')[:8]
    return render(request, 'modbusapp/dashboard.html', {'devices': devices})


def card_series(request, device_id: int, card_id: int):
    # Params: ?limit=1000 (samples), optional since=ISO8601 to bound start time
    try:
        device = ModbusDevice.objects.get(id=device_id, enabled=True)
    except ModbusDevice.DoesNotExist:
        return JsonResponse({'error': 'device not found'}, status=404)
    try:
        card = ModbusCard.objects.get(id=card_id, device=device)
    except ModbusCard.DoesNotExist:
        return JsonResponse({'error': 'card not found'}, status=404)

    try:
        limit = int(request.GET.get('limit', 300))
    except Exception:
        limit = 300
    limit = max(10, min(2000, limit))

    since_param = request.GET.get('since')
    qs = PollResult.objects.filter(device=device)
    if since_param:
        from django.utils.dateparse import parse_datetime
        dt = parse_datetime(since_param)
        if dt is not None:
            qs = qs.filter(created_at__gte=dt)
    # Fetch newest-first then reverse to chronological
    rows = list(qs.order_by('-created_at').values('created_at', 'discrete_inputs', 'input_registers', 'holding_registers', 'coils')[:limit])
    rows.reverse()

    # Determine index offset based on card source and device starts
    src = card.source
    addr = card.address
    di_start, ir_start, hr_start, coil_start = device.di_start, device.ir_start, device.hr_start, device.coil_start
    series = []
    for r in rows:
        ts = r['created_at'].isoformat()
        arr = None
        base = 0
        if src == 'di':
            arr = r['discrete_inputs'] or []
            base = di_start
        elif src == 'ir':
            arr = r['input_registers'] or []
            base = ir_start
        elif src == 'hr':
            arr = r['holding_registers'] or []
            base = hr_start
        elif src == 'coil':
            arr = r['coils'] or []
            base = coil_start
        val = None
        if isinstance(arr, list) and addr >= base:
            idx = addr - base
            if 0 <= idx < len(arr):
                v = arr[idx]
                # Normalize booleans to 0/1 for charts
                if isinstance(v, bool):
                    val = 1 if v else 0
                else:
                    try:
                        val = float(v)
                    except Exception:
                        # non-numeric, skip
                        val = None
        series.append({'t': ts, 'v': val})

    return JsonResponse({
        'device': device.id,
        'card': card.id,
        'name': card.name,
        'unit': card.unit_label,
        'source': card.source,
        'address': card.address,
        'series': series,
    })


@csrf_exempt
@require_http_methods(["POST"])
def execute_action(request, device_id: int, action_id: int):
    try:
        device = ModbusDevice.objects.get(id=device_id, enabled=True)
    except ModbusDevice.DoesNotExist:
        return JsonResponse({'error': 'device not found'}, status=404)
    try:
        action = ModbusActionCard.objects.get(id=action_id, device=device)
    except ModbusActionCard.DoesNotExist:
        return JsonResponse({'error': 'action not found'}, status=404)

    try:
        body = json.loads(request.body.decode('utf-8')) if request.body else {}
    except Exception:
        body = {}
    which = (body.get('which') or 'open').lower()
    if which not in ('open', 'close'):
        return HttpResponseBadRequest('which must be "open" or "close"')
    values = action.open_values if which == 'open' else action.close_values
    if not isinstance(values, list) or not all(isinstance(v, bool) for v in values):
        return JsonResponse({'error': 'action values misconfigured'}, status=500)
    ok, err = write_coils_to_device(device, action.start, values)
    return JsonResponse({'ok': ok, 'error': err, 'which': which}, status=200 if ok else 500)
