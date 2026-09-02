from django.contrib import admin

from .models import Bebedouro


@admin.register(Bebedouro)
class BebedouroAdmin(admin.ModelAdmin):
    list_display = ["codigo_col", "local", "ativo"]
    list_display_links = ["codigo_col"]
    list_editable = ["local", "ativo"]
    ordering = ["numero"]
    fields = ["numero", "local", "ativo"]

    @admin.display(description="Código", ordering="numero")
    def codigo_col(self, obj):
        return obj.codigo
