import asyncio
import time
from django.core.management.base import BaseCommand
from asgiref.sync import sync_to_async
from modbusapp.models import ModbusDevice, PollResult
from modbusapp.modbus_client import (
    client_for,
    read_all,
    decode_holding_registers,
    aclient_for,
    aread_all,
    AsyncModbusTcpClient,
)


class Command(BaseCommand):
    help = 'Poll configured Modbus devices and store results.'

    def add_arguments(self, parser):
        parser.add_argument('--once', action='store_true', help='Poll once and exit')
        parser.add_argument('--interval', type=float, default=1.0, help='Default interval seconds when not set per device')
        parser.add_argument('--refresh', type=float, default=5.0, help='Seconds between checking for device list changes')

    def handle(self, *args, **options):
        single = options['once']
        default_interval = options['interval']
        refresh_secs = options['refresh']

        async def fetch_devices():
            return await sync_to_async(lambda: list(ModbusDevice.objects.filter(enabled=True)[:8]))()

        async def save_result(device, data=None, ok=True, error=""):
            if data is None:
                data = {'discrete_inputs': [], 'input_registers': [], 'holding_registers': [], 'coils': []}
            await sync_to_async(PollResult.objects.create)(
                device=device,
                discrete_inputs=data.get('discrete_inputs', []),
                input_registers=data.get('input_registers', []),
                holding_registers=data.get('holding_registers', []),
                coils=data.get('coils', []),
                ok=ok,
                error=error,
            )

        async def poll_device_once(d: ModbusDevice):
            try:
                if AsyncModbusTcpClient is not None:
                    async with aclient_for(d.host, d.port) as c:
                        data = await aread_all(
                            c, d.unit_id,
                            d.di_start, d.di_count,
                            d.ir_start, d.ir_count,
                            d.hr_start, d.hr_count,
                            d.coil_start, d.coil_count,
                        )
                else:
                    # Fallback: run sync read in a thread
                    def sync_read():
                        with client_for(d.host, d.port) as c:
                            return read_all(
                                c, d.unit_id,
                                d.di_start, d.di_count,
                                d.ir_start, d.ir_count,
                                d.hr_start, d.hr_count,
                                d.coil_start, d.coil_count,
                            )
                    data = await asyncio.to_thread(sync_read)

                if data.get('holding_registers'):
                    decoded = decode_holding_registers(
                        data['holding_registers'],
                        datatype=d.hr_datatype,
                        byte_order=d.hr_byte_order,
                        word_order=d.hr_word_order,
                    )
                    # Optional rounding for floats
                    if d.hr_datatype in ("f32", "f64") and isinstance(decoded, list):
                        try:
                            places = max(0, int(getattr(d, 'hr_decimals', 2)))
                        except Exception:
                            places = 2
                        data['holding_registers'] = [
                            (round(v, places) if isinstance(v, float) else v)
                            for v in decoded
                        ]
                    else:
                        data['holding_registers'] = decoded
                await save_result(d, data=data, ok=True)
                self.stdout.write(self.style.SUCCESS(f"Polled {d}"))
            except Exception as e:
                await save_result(d, ok=False, error=str(e))
                self.stderr.write(self.style.ERROR(f"Error polling {d}: {e}"))

        async def run_once():
            devices = await fetch_devices()
            await asyncio.gather(*(poll_device_once(d) for d in devices))

        async def device_worker(device_id: int):
            # Initial slight stagger to avoid thundering herd
            await asyncio.sleep((device_id % 10) * 0.05)
            while True:
                # Always fetch the latest device config each cycle
                try:
                    d = await sync_to_async(ModbusDevice.objects.get)(pk=device_id)
                except ModbusDevice.DoesNotExist:
                    break
                if not d.enabled:
                    break
                interval = max(0.1, (d.poll_interval_ms or int(default_interval * 1000)) / 1000.0)
                start = time.time()
                await poll_device_once(d)
                elapsed = time.time() - start
                await asyncio.sleep(max(0.0, interval - elapsed))

        async def run_forever():
            import contextlib
            tasks: dict[int, asyncio.Task] = {}
            while True:
                devices = await fetch_devices()
                current_ids = {d.id for d in devices}
                # Start new tasks
                for did in current_ids - set(tasks.keys()):
                    tasks[did] = asyncio.create_task(device_worker(did))
                # Cancel tasks for removed/disabled devices
                for did in list(tasks.keys() - current_ids):
                    t = tasks.pop(did)
                    t.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await t
                await asyncio.sleep(max(0.5, float(refresh_secs)))

        if single:
            asyncio.run(run_once())
        else:
            import contextlib
            try:
                asyncio.run(run_forever())
            except KeyboardInterrupt:
                self.stdout.write("Stopped")
