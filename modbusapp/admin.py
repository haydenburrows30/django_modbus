from django.contrib import admin
from .models import ModbusDevice, PollResult, ModbusCard


@admin.register(ModbusDevice)
class ModbusDeviceAdmin(admin.ModelAdmin):
    list_display = ("name", "host", "port", "unit_id", "enabled", "hr_datatype", "hr_byte_order", "hr_word_order")
    list_filter = ("enabled",)
    fieldsets = (
        (None, {
            'fields': ("name", "enabled")
        }),
        ("Connection", {
            'fields': ("host", "port", "unit_id", "poll_interval_ms"),
        }),
        ("Ranges", {
            'fields': (
                ("di_start", "di_count"),
                ("ir_start", "ir_count"),
                ("hr_start", "hr_count"),
                ("coil_start", "coil_count"),
            )
        }),
        ("Holding Decode", {
            'fields': ("hr_datatype", ("hr_byte_order", "hr_word_order"), "hr_decimals"),
        }),
    )


@admin.register(PollResult)
class PollResultAdmin(admin.ModelAdmin):
    list_display = ("device", "created_at", "ok")
    list_filter = ("ok", "device")
    readonly_fields = ("created_at",)


@admin.register(ModbusCard)
class ModbusCardAdmin(admin.ModelAdmin):
    list_display = ("device", "order", "name", "source", "address", "unit_label", "decimals")
    list_filter = ("device", "source")
    search_fields = ("name",)
    ordering = ("device", "order", "id")
