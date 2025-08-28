from django.db import models


class ModbusDevice(models.Model):
    name = models.CharField(max_length=100)
    host = models.CharField(max_length=200)
    port = models.IntegerField(default=502)
    unit_id = models.IntegerField(default=1)
    enabled = models.BooleanField(default=True)

    # Address ranges to poll (inclusive start, count)
    di_start = models.IntegerField(default=0)
    di_count = models.IntegerField(default=0)
    ir_start = models.IntegerField(default=0)
    ir_count = models.IntegerField(default=0)
    hr_start = models.IntegerField(default=0)
    hr_count = models.IntegerField(default=0)
    # Holding register decode configuration
    HR_DATATYPE_CHOICES = [
        ("u16", "Unsigned 16-bit"),
        ("s16", "Signed 16-bit"),
        ("u32", "Unsigned 32-bit"),
        ("s32", "Signed 32-bit"),
        ("f32", "Float 32-bit"),
        ("u64", "Unsigned 64-bit"),
        ("s64", "Signed 64-bit"),
        ("f64", "Float 64-bit"),
    ]
    hr_datatype = models.CharField(max_length=3, choices=HR_DATATYPE_CHOICES, default="u16")
    BYTE_ORDER_CHOICES = [("big", "Big-endian"), ("little", "Little-endian")]
    WORD_ORDER_CHOICES = [("big", "MSW first"), ("little", "LSW first")]
    hr_byte_order = models.CharField(max_length=6, choices=BYTE_ORDER_CHOICES, default="big")
    hr_word_order = models.CharField(max_length=6, choices=WORD_ORDER_CHOICES, default="big")
    # Optional display precision for decoded floats
    hr_decimals = models.IntegerField(default=2)
    coil_start = models.IntegerField(default=0)
    coil_count = models.IntegerField(default=0)

    poll_interval_ms = models.IntegerField(default=1000)

    def __str__(self):
        return f"{self.name} ({self.host}:{self.port} u{self.unit_id})"


class PollResult(models.Model):
    device = models.ForeignKey(ModbusDevice, on_delete=models.CASCADE, related_name='polls')
    created_at = models.DateTimeField(auto_now_add=True)
    # Store as JSON for flexibility
    discrete_inputs = models.JSONField(default=list)
    input_registers = models.JSONField(default=list)
    holding_registers = models.JSONField(default=list)
    coils = models.JSONField(default=list)
    ok = models.BooleanField(default=True)
    error = models.TextField(blank=True, default="")

    class Meta:
        ordering = ['-created_at']


class ModbusCard(models.Model):
    SOURCE_CHOICES = [
        ('hr', 'Holding Register'),
        ('ir', 'Input Register'),
        ('di', 'Discrete Input'),
        ('coil', 'Coil'),
    ]
    device = models.ForeignKey(ModbusDevice, on_delete=models.CASCADE, related_name='cards')
    name = models.CharField(max_length=100)
    source = models.CharField(max_length=4, choices=SOURCE_CHOICES, default='hr')
    address = models.IntegerField(help_text='Absolute Modbus address within the selected source')
    unit_label = models.CharField(max_length=32, blank=True, default='')
    decimals = models.IntegerField(null=True, blank=True, help_text='Override decimals for display (optional)')
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['device_id', 'order', 'id']

    def __str__(self):
        return f"{self.device.name}: {self.name} ({self.source}@{self.address})"


class ModbusActionCard(models.Model):
    device = models.ForeignKey(ModbusDevice, on_delete=models.CASCADE, related_name='actions')
    name = models.CharField(max_length=100)
    start = models.IntegerField(help_text='Starting coil address to write')
    open_values = models.JSONField(default=list, help_text='List of booleans to write for OPEN')
    close_values = models.JSONField(default=list, help_text='List of booleans to write for CLOSE')
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['device_id', 'order', 'id']

    def __str__(self):
        return f"{self.device.name}: {self.name} (coils@{self.start})"
