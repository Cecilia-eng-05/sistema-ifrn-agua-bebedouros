from django.contrib import admin

from .models import Bebedouro

admin.site.site_header = "Monitoramento e Gestão da Água — IFRN-CNAT"
admin.site.site_title = "Monitoramento da Água"
admin.site.index_title = "Cadastro e administração"


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
