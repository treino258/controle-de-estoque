from datetime import date


def format_price_variation(
    current_price,
    previous_price,
):

    # Primeira compra
    if previous_price is None:

        return f"""
        <span style="
            font-weight: 600;
            font-size: 15px;
        ">
            R$ {current_price:.2f}
        </span>
        """

    # Mais caro
    if current_price > previous_price:

        return f"""
        <span style="
            color: #ef4444;
            font-weight: 700;
            font-size: 15px;
        ">
            🔺 R$ {current_price:.2f}
        </span>
        """

    # Mais barato
    if current_price < previous_price:

        return f"""
        <span style="
            color: #22c55e;
            font-weight: 700;
            font-size: 15px;
        ">
            🔻 R$ {current_price:.2f}
        </span>
        """

    # Mesmo preço
    return f"""
    <span style="
        font-weight: 600;
        font-size: 15px;
    ">
        R$ {current_price:.2f}
    </span>
    """



def format_data_compra_badge(data_compra):

    data_formatada = (
        data_compra.strftime("%d/%m/%Y")
    )

    return data_formatada