from datetime import date

from django.contrib import admin

from .models import Bebedouro

admin.site.site_header = "Monitoramento e Gestão da Água — IFRN-CNAT"
admin.site.site_title = "Monitoramento da Água"
admin.site.index_title = "Cadastro e administração"


@admin.register(Bebedouro)
class BebedouroAdmin(admin.ModelAdmin):
    list_display = ["codigo_col", "local", "situacao"]
    list_display_links = ["codigo_col"]
    list_editable = ["local"]
    ordering = ["numero"]
    fields = ["numero", "local", "desativado_em", "foto"]
    actions = ["desativar_hoje", "reativar"]

    @admin.display(description="Código", ordering="numero")
    def codigo_col(self, obj):
        return obj.codigo

    @admin.display(description="Situação")
    def situacao(self, obj):
        if obj.desativado_em is None:
            return "Em operação"
        return f"Desativado em {obj.desativado_em:%d/%m/%Y}"

    @admin.action(description="Desativar (a partir de hoje)")
    def desativar_hoje(self, request, queryset):
        n = queryset.filter(desativado_em__isnull=True).update(desativado_em=date.today())
        self.message_user(request, f"{n} bebedouro(s) desativado(s) a partir de hoje.")

    @admin.action(description="Reativar (voltar à operação)")
    def reativar(self, request, queryset):
        n = queryset.filter(desativado_em__isnull=False).update(desativado_em=None)
        self.message_user(request, f"{n} bebedouro(s) reativado(s).")
