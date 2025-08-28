import logging
from django.core.management.base import BaseCommand
from pymodbus.client import ModbusTcpClient


class Command(BaseCommand):
    help = "Diagnose a Modbus TCP device by testing connection and reads for coils, DIs, IRs, HRs."

    def add_arguments(self, parser):
        parser.add_argument('--host', required=True, help='Device IP/host')
        parser.add_argument('--port', type=int, default=502, help='TCP port (default 502)')
        parser.add_argument('--unit', type=int, default=1, help='Unit ID / slave ID')
        parser.add_argument('--timeout', type=float, default=3.0, help='Socket timeout seconds')
        parser.add_argument('--debug', action='store_true', help='Enable pymodbus debug logging')
        # Ranges
        parser.add_argument('--di-start', type=int, default=0)
        parser.add_argument('--di-count', type=int, default=0)
        parser.add_argument('--ir-start', type=int, default=0)
        parser.add_argument('--ir-count', type=int, default=0)
        parser.add_argument('--hr-start', type=int, default=0)
        parser.add_argument('--hr-count', type=int, default=0)
        parser.add_argument('--coil-start', type=int, default=0)
        parser.add_argument('--coil-count', type=int, default=0)

    def handle(self, *args, **opts):
        if opts['debug']:
            logging.basicConfig(level=logging.DEBUG)
        host = opts['host']
        port = opts['port']
        unit = opts['unit']
        timeout = opts['timeout']
        self.stdout.write(self.style.NOTICE(f"Connecting to {host}:{port} (unit {unit}) timeout={timeout}s"))
        client = ModbusTcpClient(host=host, port=port, timeout=timeout)
        try:
            if not client.connect():
                self.stderr.write(self.style.ERROR("TCP connect failed"))
                return 1
            self.stdout.write(self.style.SUCCESS("TCP connect OK"))

            def check_result(name, rr, attr, slicer=lambda x: x):
                if rr is None:
                    self.stderr.write(self.style.ERROR(f"{name}: No response"))
                    return
                if hasattr(rr, 'isError') and rr.isError():
                    self.stderr.write(self.style.ERROR(f"{name}: {rr}"))
                else:
                    data = getattr(rr, attr, None)
                    if data is None:
                        self.stdout.write(f"{name}: OK (no {attr}) -> {rr}")
                    else:
                        vals = list(slicer(data))
                        self.stdout.write(f"{name}: OK -> {vals[:32]}{' …' if len(vals) > 32 else ''}")

            # Discrete Inputs
            if opts['di_count'] > 0:
                rr = client.read_discrete_inputs(address=opts['di_start'], count=opts['di_count'], unit=unit)
                check_result("Discrete Inputs", rr, 'bits')

            # Input Registers
            if opts['ir_count'] > 0:
                rr = client.read_input_registers(address=opts['ir_start'], count=opts['ir_count'], unit=unit)
                check_result("Input Registers", rr, 'registers')

            # Holding Registers
            if opts['hr_count'] > 0:
                rr = client.read_holding_registers(address=opts['hr_start'], count=opts['hr_count'], unit=unit)
                check_result("Holding Registers", rr, 'registers')

            # Coils
            if opts['coil_count'] > 0:
                rr = client.read_coils(address=opts['coil_start'], count=opts['coil_count'], unit=unit)
                check_result("Coils", rr, 'bits')

            self.stdout.write(self.style.SUCCESS("Diagnostics complete"))
        finally:
            try:
                client.close()
            except Exception:
                pass
