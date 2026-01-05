def calculate_print_cost(
    grams: float,
    material_cost_per_gram: float,
    hours: float,
    machine_hourly_rate: float,
    processing_fee: float,
    waste_pct: float,
    markup: float,
    discount_pct: float,
    is_donation: bool,
    round_to_nearest: bool
) -> dict:
    """
    Calculates the cost and final price of a 3D print job.
    """
    # Material Cost
    raw_mat_cost = material_cost_per_gram * grams
    mat_total = raw_mat_cost * (1 + waste_pct)

    # Machine Cost
    machine_cost = hours * machine_hourly_rate

    # Base Cost (Total Cost to Produce)
    base_cost = mat_total + machine_cost + processing_fee

    # Pricing
    subtotal = base_cost * markup
    discount_amt = subtotal * discount_pct
    final_price = subtotal - discount_amt

    if round_to_nearest:
        final_price = round(final_price)

    if is_donation:
        final_price = 0.00

    profit = final_price - base_cost
    margin = (profit / final_price * 100) if final_price > 0 else 0

    return {
        "mat_total": mat_total,
        "machine_cost": machine_cost,
        "base_cost": base_cost,
        "subtotal": subtotal,
        "discount_amt": discount_amt,
        "final_price": final_price,
        "profit": profit,
        "margin": margin
    }
