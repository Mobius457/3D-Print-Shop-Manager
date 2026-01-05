import pytest
from src.logic import calculate_print_cost

def test_calculate_print_cost_basic():
    """Test basic cost calculation without waste or discounts."""
    result = calculate_print_cost(
        grams=100,
        material_cost_per_gram=0.02, # $20/kg -> $0.02/g
        hours=5,
        machine_hourly_rate=0.75,
        processing_fee=2.00,
        waste_pct=0.0,
        markup=2.5,
        discount_pct=0.0,
        is_donation=False,
        round_to_nearest=False
    )

    # Material: 100 * 0.02 = 2.00
    # Machine: 5 * 0.75 = 3.75
    # Processing: 2.00
    # Base Cost = 2.00 + 3.75 + 2.00 = 7.75
    # Price = 7.75 * 2.5 = 19.375

    assert result["mat_total"] == 2.00
    assert result["machine_cost"] == 3.75
    assert result["base_cost"] == 7.75
    assert result["final_price"] == 19.375
    assert result["profit"] == 19.375 - 7.75

def test_calculate_print_cost_waste():
    """Test with 20% waste."""
    result = calculate_print_cost(
        grams=100,
        material_cost_per_gram=0.02,
        hours=0,
        machine_hourly_rate=0,
        processing_fee=0,
        waste_pct=0.20,
        markup=1.0,
        discount_pct=0.0,
        is_donation=False,
        round_to_nearest=False
    )

    # Material: 100 * 0.02 * 1.2 = 2.40
    assert result["mat_total"] == 2.40
    assert result["base_cost"] == 2.40

def test_calculate_print_cost_donation():
    """Test donation (price should be 0)."""
    result = calculate_print_cost(
        grams=100,
        material_cost_per_gram=0.02,
        hours=1,
        machine_hourly_rate=1.00,
        processing_fee=0,
        waste_pct=0.0,
        markup=2.0,
        discount_pct=0.0,
        is_donation=True,
        round_to_nearest=False
    )

    assert result["final_price"] == 0.00
    assert result["profit"] < 0 # Should be negative (loss of material/time)
    assert result["profit"] == -3.00 # -(2.00 + 1.00)

def test_calculate_print_cost_rounding():
    """Test rounding to nearest dollar."""
    result = calculate_print_cost(
        grams=1,
        material_cost_per_gram=1.00,
        hours=0,
        machine_hourly_rate=0,
        processing_fee=0,
        waste_pct=0.0,
        markup=1.0,
        discount_pct=0.0,
        is_donation=False,
        round_to_nearest=True
    )

    # Cost 1.00 -> Price 1.00.
    # Let's try something that rounds up.
    # Cost 1.60 -> Price 1.60 -> Round to 2.00

    result2 = calculate_print_cost(
        grams=1.6,
        material_cost_per_gram=1.0,
        hours=0,
        machine_hourly_rate=0,
        processing_fee=0,
        waste_pct=0.0,
        markup=1.0,
        discount_pct=0.0,
        is_donation=False,
        round_to_nearest=True
    )

    assert result2["final_price"] == 2.00
