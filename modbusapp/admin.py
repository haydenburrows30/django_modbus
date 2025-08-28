from django.contrib import admin
from django.contrib import messages
from .models import ModbusDevice, PollResult, ModbusCard, ModbusActionCard


@admin.register(ModbusDevice)
class ModbusDeviceAdmin(admin.ModelAdmin):
    list_display = ("name", "host", "port", "unit_id", "enabled", "hr_datatype", "hr_byte_order", "hr_word_order")
    list_filter = ("enabled",)
    save_as = True  # enables "Save as new" to clone a device and then change the name
    actions = ["duplicate_devices"]
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

    @admin.action(description="Duplicate selected devices")
    def duplicate_devices(self, request, queryset):
        created = 0
        for obj in queryset:
            dup = ModbusDevice(
                name=f"Copy of {obj.name}",
                host=obj.host,
                port=obj.port,
                unit_id=obj.unit_id,
                enabled=obj.enabled,
                di_start=obj.di_start,
                di_count=obj.di_count,
                ir_start=obj.ir_start,
                ir_count=obj.ir_count,
                hr_start=obj.hr_start,
                hr_count=obj.hr_count,
                hr_datatype=obj.hr_datatype,
                hr_byte_order=obj.hr_byte_order,
                hr_word_order=obj.hr_word_order,
                hr_decimals=obj.hr_decimals,
                coil_start=obj.coil_start,
                coil_count=obj.coil_count,
                poll_interval_ms=obj.poll_interval_ms,
            )
            dup.save()
            created += 1
        if created:
            self.message_user(request, f"Duplicated {created} device(s).", level=messages.SUCCESS)
        else:
            self.message_user(request, "No devices duplicated.", level=messages.INFO)


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


@admin.register(ModbusActionCard)
class ModbusActionCardAdmin(admin.ModelAdmin):
    list_display = ("device", "order", "name", "start")
    list_filter = ("device",)
    search_fields = ("name",)
    ordering = ("device", "order", "id")
