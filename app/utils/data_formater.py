from datetime import date


def format_validade(data_validade):

    if not data_validade:
        return "-"

    dias_restantes = (
        data_validade - date.today()
    ).days

    data_formatada = (
        data_validade.strftime("%d/%m/%Y")
    )

    cor_texto = "inherit"

    

    if dias_restantes <= 7:

        cor_texto = "#b91c1c"

    if dias_restantes >= 60:

        meses = dias_restantes // 30
        dias = dias_restantes % 30

        if dias > 0:

            return (
                f"{data_formatada}<br>"
                f"({meses} meses e {dias} dias)"
            )

        return (
            f"{data_formatada}<br>"
            f"({meses} meses)"
        )
    
    if dias_restantes < 0:
        cor_texto = "#3F3007"
        texto_tempo = "(expirada)"

    else:
        texto_tempo = f"({dias_restantes} dias)"

    return f"""
    {data_formatada}<br>

    <span style="
        color: {cor_texto};
        font-weight: 600;
    ">
        {texto_tempo}
    </span>
    """