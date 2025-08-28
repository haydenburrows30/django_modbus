import json
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
from .models import ModbusDevice, PollResult
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
    devices = ModbusDevice.objects.filter(enabled=True).prefetch_related('cards').order_by('id')[:8]
    return render(request, 'modbusapp/dashboard.html', {'devices': devices})
