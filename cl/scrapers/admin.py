from django.contrib import admin

from cl.scrapers.models import (
    UrlHash, ErrorLog, PACERFreeDocumentLog, PACERFreeDocumentRow
)


@admin.register(ErrorLog)
class ErrorLogAdmin(admin.ModelAdmin):
    readonly_fields = ('log_time', 'log_level', 'court', 'message',)
    list_display = ('log_level', 'log_time', 'court')
    list_filter = ('court',)


@admin.register(PACERFreeDocumentLog)
class PACERFreeDocumentLogAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'court_id', 'status', 'date_started',
                    'date_completed', 'date_queried')
    list_filter = ('status', 'court__jurisdiction')
    list_editable = ('status',)
    ordering = ('-date_started',)


admin.site.register(PACERFreeDocumentRow)
admin.site.register(UrlHash)
