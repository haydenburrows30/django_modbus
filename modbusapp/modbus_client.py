from contextlib import contextmanager, asynccontextmanager
from typing import List, Tuple, Any
from pymodbus.client import ModbusTcpClient
try:
    from pymodbus.client import AsyncModbusTcpClient  # pymodbus >=3
except Exception:  # pragma: no cover
    AsyncModbusTcpClient = None  # type: ignore
import struct
import inspect


@contextmanager
def client_for(host: str, port: int):
    client = ModbusTcpClient(host=host, port=port)
    try:
        client.connect()
        yield client
    finally:
        try:
            client.close()
        except Exception:
            pass


def _call_with_unit_or_slave(method: Any, *, address: int, unit_id: int, count: int | None = None, values: List[bool] | None = None):
    """Call pymodbus methods using whichever kwarg the method supports: 'unit' or 'slave'.
    Uses inspect.signature to choose the correct name and avoids positional ambiguity.
    """
    sig = inspect.signature(method)
    params = sig.parameters
    key = 'unit' if 'unit' in params else ('slave' if 'slave' in params else None)
    kwargs = {'address': address}
    if count is not None:
        kwargs['count'] = count
    if values is not None:
        kwargs['values'] = values
    if key:
        kwargs[key] = unit_id
    try:
        return method(**kwargs)
    except TypeError as e:
        # If the first guess fails and both names are available, try the other
        if key == 'unit' and 'slave' in params:
            kwargs.pop('unit', None)
            kwargs['slave'] = unit_id
            return method(**kwargs)
        if key == 'slave' and 'unit' in params:
            kwargs.pop('slave', None)
            kwargs['unit'] = unit_id
            return method(**kwargs)
        raise


# Async variants
@asynccontextmanager
async def aclient_for(host: str, port: int):
    if AsyncModbusTcpClient is None:
        raise RuntimeError("AsyncModbusTcpClient not available in installed pymodbus")
    client = AsyncModbusTcpClient(host=host, port=port)
    try:
        await client.connect()
        yield client
    finally:
        try:
            await client.close()
        except Exception:
            pass


async def _acall_with_unit_or_slave(method: Any, *, address: int, unit_id: int, count: int | None = None, values: List[bool] | None = None):
    sig = inspect.signature(method)
    params = sig.parameters
    key = 'unit' if 'unit' in params else ('slave' if 'slave' in params else None)
    kwargs = {'address': address}
    if count is not None:
        kwargs['count'] = count
    if values is not None:
        kwargs['values'] = values
    if key:
        kwargs[key] = unit_id
    try:
        return await method(**kwargs)
    except TypeError:
        if key == 'unit' and 'slave' in params:
            kwargs.pop('unit', None)
            kwargs['slave'] = unit_id
            return await method(**kwargs)
        if key == 'slave' and 'unit' in params:
            kwargs.pop('slave', None)
            kwargs['unit'] = unit_id
            return await method(**kwargs)
        raise


def read_all(client: ModbusTcpClient, unit_id: int, di_start: int, di_count: int,
             ir_start: int, ir_count: int, hr_start: int, hr_count: int,
             coil_start: int, coil_count: int,
             hr_decode: dict | None = None):
    result = {
        'discrete_inputs': [],
        'input_registers': [],
        'holding_registers': [],
        'coils': [],
    }
    # Discrete Inputs
    if di_count > 0:
        rr = _call_with_unit_or_slave(client.read_discrete_inputs, address=di_start, count=di_count, unit_id=unit_id)
        result['discrete_inputs'] = list(rr.bits) if hasattr(rr, 'bits') else []
    # Input Registers
    if ir_count > 0:
        rr = _call_with_unit_or_slave(client.read_input_registers, address=ir_start, count=ir_count, unit_id=unit_id)
        result['input_registers'] = list(rr.registers) if hasattr(rr, 'registers') else []
    # Holding Registers
    if hr_count > 0:
        rr = _call_with_unit_or_slave(client.read_holding_registers, address=hr_start, count=hr_count, unit_id=unit_id)
        result['holding_registers'] = list(rr.registers) if hasattr(rr, 'registers') else []
    # Coils
    if coil_count > 0:
        rr = _call_with_unit_or_slave(client.read_coils, address=coil_start, count=coil_count, unit_id=unit_id)
        result['coils'] = list(rr.bits) if hasattr(rr, 'bits') else []
    return result


async def aread_all(client: Any, unit_id: int, di_start: int, di_count: int,
                    ir_start: int, ir_count: int, hr_start: int, hr_count: int,
                    coil_start: int, coil_count: int):
    result = {
        'discrete_inputs': [],
        'input_registers': [],
        'holding_registers': [],
        'coils': [],
    }
    if di_count > 0:
        rr = await _acall_with_unit_or_slave(client.read_discrete_inputs, address=di_start, count=di_count, unit_id=unit_id)
        result['discrete_inputs'] = list(getattr(rr, 'bits', []) or [])
    if ir_count > 0:
        rr = await _acall_with_unit_or_slave(client.read_input_registers, address=ir_start, count=ir_count, unit_id=unit_id)
        result['input_registers'] = list(getattr(rr, 'registers', []) or [])
    if hr_count > 0:
        rr = await _acall_with_unit_or_slave(client.read_holding_registers, address=hr_start, count=hr_count, unit_id=unit_id)
        result['holding_registers'] = list(getattr(rr, 'registers', []) or [])
    if coil_count > 0:
        rr = await _acall_with_unit_or_slave(client.read_coils, address=coil_start, count=coil_count, unit_id=unit_id)
        result['coils'] = list(getattr(rr, 'bits', []) or [])
    return result


def decode_holding_registers(regs: List[int], datatype: str = "u16", byte_order: str = "big", word_order: str = "big") -> List[float | int]:
    """Decode a sequence of 16-bit holding registers into typed values.
    datatype: one of u16,s16,u32,s32,f32,u64,s64,f64
    byte_order: 'big' or 'little' (byte order within each 16-bit register)
    word_order: 'big' (MSW first) or 'little' (LSW first) for multi-register values
    """
    if not regs:
        return []
    sizes = {
        'u16': (1, 'H'), 's16': (1, 'h'),
        'u32': (2, 'I'), 's32': (2, 'i'), 'f32': (2, 'f'),
        'u64': (4, 'Q'), 's64': (4, 'q'), 'f64': (4, 'd'),
    }
    if datatype not in sizes:
        return regs  # unknown datatype, return raw
    words_per, fmt = sizes[datatype]
    endian = '>' if byte_order == 'big' else '<'
    out: List[float | int] = []
    total = len(regs) - (len(regs) % words_per)
    for i in range(0, total, words_per):
        chunk = regs[i:i + words_per]
        if words_per > 1 and word_order == 'little':
            chunk = list(reversed(chunk))
        b = bytearray()
        for r in chunk:
            b.extend(int(r & 0xFFFF).to_bytes(2, byteorder=byte_order, signed=False))
        try:
            val = struct.unpack(endian + fmt, bytes(b))[0]
        except struct.error:
            # If unpack fails (bad length), stop decoding further
            break
        out.append(val)
    return out


def write_coils_to_device(device, start: int, values: List[bool]) -> Tuple[bool, str]:
    try:
        with client_for(device.host, device.port) as c:
            rr = _call_with_unit_or_slave(c.write_coils, address=start, values=values, unit_id=device.unit_id)
            if hasattr(rr, 'isError') and rr.isError():
                return False, str(rr)
        return True, ''
    except Exception as e:
        return False, str(e)


async def awrite_coils_to_device(device, start: int, values: List[bool]) -> Tuple[bool, str]:
    if AsyncModbusTcpClient is None:
        return False, "AsyncModbusTcpClient not available"
    try:
        async with aclient_for(device.host, device.port) as c:
            rr = await _acall_with_unit_or_slave(c.write_coils, address=start, values=values, unit_id=device.unit_id)
            if hasattr(rr, 'isError') and rr.isError():
                return False, str(rr)
        return True, ''
    except Exception as e:
        return False, str(e)
