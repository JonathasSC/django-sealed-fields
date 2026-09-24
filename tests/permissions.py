def allow_title_publico(user, obj, field_name):
    """
    Regra de permissão customizada usada nos testes.
    """
    return obj.title == "publico"
