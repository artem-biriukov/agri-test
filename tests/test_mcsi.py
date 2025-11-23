import pytest
import sys
from pathlib import Path

# Add ml_models to path
sys.path.insert(0, str(Path(__file__).parent.parent / "ml_models" / "mcsi"))

from mcsi_algorithm import calculate_mcsi, calculate_water_stress, calculate_heat_stress


class TestMCSIAlgorithm:
    """Test suite for MCSI (Multivariate Corn Stress Index) algorithm."""

    def test_calculate_water_stress_no_deficit(self):
        """Test water stress with no water deficit (surplus)."""
        stress = calculate_water_stress(deficit_mm=-5.0)
        assert stress == 0, "Surplus water should result in 0 stress"

    def test_calculate_water_stress_minimal(self):
        """Test water stress with minimal deficit."""
        stress = calculate_water_stress(deficit_mm=1.5)
        assert 0 <= stress <= 30, "Minimal deficit (0-2mm) should have low stress"

    def test_calculate_water_stress_moderate(self):
        """Test water stress with moderate deficit."""
        stress = calculate_water_stress(deficit_mm=3.0)
        assert 30 < stress <= 70, "Moderate deficit (2-4mm) should have moderate stress"

    def test_calculate_water_stress_high(self):
        """Test water stress with high deficit."""
        stress = calculate_water_stress(deficit_mm=5.0)
        assert 50 < stress <= 100, "High deficit (4-6mm) should have high stress"

    def test_calculate_water_stress_severe(self):
        """Test water stress with severe deficit."""
        stress = calculate_water_stress(deficit_mm=8.0)
        assert stress == 100, "Severe deficit (>6mm) should result in 100 stress"

    def test_calculate_water_stress_pollination_multiplier(self):
        """Test water stress with pollination period multiplier."""
        stress_normal = calculate_water_stress(deficit_mm=3.0, is_pollination=False)
        stress_pollination = calculate_water_stress(deficit_mm=3.0, is_pollination=True)
        
        assert stress_pollination > stress_normal, "Pollination period should increase stress"
        assert stress_pollination / stress_normal == pytest.approx(1.5, rel=0.1), \
            "Pollination multiplier should be ~1.5x"

    def test_calculate_heat_stress_normal(self):
        """Test heat stress with normal temperature."""
        stress = calculate_heat_stress(lst_mean=25.0)
        assert stress == 0, "Normal temperature (<35°C) should have no heat stress"

    def test_calculate_heat_stress_mild(self):
        """Test heat stress with mild heat."""
        stress = calculate_heat_stress(lst_mean=36.0, days_above_35=3)
        assert 0 < stress < 50, "Mild heat should result in low-moderate stress"

    def test_calculate_heat_stress_severe(self):
        """Test heat stress with severe heat."""
        stress = calculate_heat_stress(lst_mean=40.0, days_above_38=5)
        assert stress > 80, "Severe heat (>38°C for multiple days) should be high stress"

    def test_calculate_heat_stress_pollination_multiplier(self):
        """Test heat stress with pollination period multiplier."""
        stress_normal = calculate_heat_stress(
            lst_mean=37.0, days_above_35=3, is_pollination=False
        )
        stress_pollination = calculate_heat_stress(
            lst_mean=37.0, days_above_35=3, is_pollination=True
        )
        
        assert stress_pollination > stress_normal, "Pollination period should increase stress"
        assert stress_pollination / stress_normal == pytest.approx(1.5, rel=0.1)

    def test_calculate_mcsi_all_zeros(self):
        """Test MCSI with all zero stress components."""
        csi = calculate_mcsi(
            water_stress=0,
            heat_stress=0,
            vegetation_stress=0,
            atmospheric_stress=0
        )
        assert csi == 0, "All zero components should result in CSI=0"

    def test_calculate_mcsi_all_max(self):
        """Test MCSI with all max stress components."""
        csi = calculate_mcsi(
            water_stress=100,
            heat_stress=100,
            vegetation_stress=100,
            atmospheric_stress=100
        )
        assert csi == 100, "All max components should result in CSI=100"

    def test_calculate_mcsi_weighted_average(self):
        """Test MCSI weighted average calculation."""
        # Expected: 0.40*80 + 0.30*60 + 0.20*40 + 0.10*20 = 32 + 18 + 8 + 2 = 60
        csi = calculate_mcsi(
            water_stress=80,
            heat_stress=60,
            vegetation_stress=40,
            atmospheric_stress=20
        )
        assert csi == pytest.approx(60.0, rel=0.01), "MCSI should weight components correctly"

    def test_calculate_mcsi_realistic_scenario(self):
        """Test MCSI with realistic drought scenario."""
        csi = calculate_mcsi(
            water_stress=75,  # High water stress
            heat_stress=60,   # Moderate heat
            vegetation_stress=50,  # Moderate vegetation anomaly
            atmospheric_stress=40   # Moderate atmospheric stress
        )
        assert 50 < csi < 70, "Drought scenario should result in moderate-high stress"

    def test_mcsi_range(self):
        """Test that MCSI always returns value in [0, 100] range."""
        test_cases = [
            (0, 0, 0, 0),
            (100, 100, 100, 100),
            (50, 50, 50, 50),
            (25, 75, 10, 100),
            (90, 20, 80, 10),
        ]
        
        for water, heat, veg, atm in test_cases:
            csi = calculate_mcsi(water, heat, veg, atm)
            assert 0 <= csi <= 100, f"CSI {csi} out of range [0,100]"

    def test_mcsi_water_dominance(self):
        """Test that water stress has highest weight (40%)."""
        # Same other stresses, increase water
        csi1 = calculate_mcsi(50, 50, 50, 50)
        csi2 = calculate_mcsi(100, 50, 50, 50)
        
        increase = csi2 - csi1
        # Should be 0.40 * (100-50) = 20
        assert increase == pytest.approx(20, rel=0.01), \
            "Water stress should have 40% weight"

    def test_mcsi_heat_second_importance(self):
        """Test that heat stress has second highest weight (30%)."""
        csi1 = calculate_mcsi(50, 50, 50, 50)
        csi2 = calculate_mcsi(50, 100, 50, 50)
        
        increase = csi2 - csi1
        # Should be 0.30 * (100-50) = 15
        assert increase == pytest.approx(15, rel=0.01), \
            "Heat stress should have 30% weight"


class TestMCSIEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_missing_data_handling(self):
        """Test handling of missing/NaN values."""
        with pytest.raises((ValueError, TypeError)):
            calculate_mcsi(float('nan'), 50, 50, 50)

    def test_negative_stress_values(self):
        """Test that negative stress values are handled."""
        # Negative values should either be clipped or raise error
        try:
            csi = calculate_mcsi(-10, 50, 50, 50)
            # If allowed, should be clipped
            assert csi >= 0, "CSI should never be negative"
        except ValueError:
            # Also acceptable to raise error
            pass

    def test_stress_exceeding_100(self):
        """Test stress values exceeding 100."""
        csi = calculate_mcsi(150, 50, 50, 50)
        # Should clip or raise error
        assert 0 <= csi <= 100, "CSI should always be in [0,100]"

    def test_float_precision(self):
        """Test handling of floating point precision."""
        csi1 = calculate_mcsi(33.333, 33.333, 33.333, 33.333)
        csi2 = calculate_mcsi(33.3333, 33.3333, 33.3333, 33.3333)
        
        # Should be approximately equal (within floating point error)
        assert abs(csi1 - csi2) < 1e-6


class TestMCSIIntegration:
    """Integration tests combining multiple calculations."""

    def test_weekly_stress_progression(self):
        """Test realistic weekly stress progression during drought."""
        # Week 1: Beginning of drought
        csi_week1 = calculate_mcsi(30, 20, 25, 15)
        
        # Week 2: Drought intensifies
        csi_week2 = calculate_mcsi(60, 45, 50, 35)
        
        # Week 3: Peak drought
        csi_week3 = calculate_mcsi(90, 70, 75, 60)
        
        # Stress should increase over time
        assert csi_week1 < csi_week2 < csi_week3, \
            "Stress should increase during intensifying drought"

    def test_recovery_from_drought(self):
        """Test stress reduction after rainfall."""
        # During drought
        csi_drought = calculate_mcsi(80, 60, 70, 50)
        
        # After rainfall (water deficit reduced)
        csi_recovery = calculate_mcsi(30, 60, 50, 50)
        
        assert csi_recovery < csi_drought, \
            "Stress should decrease after water becomes available"

    def test_multiple_stressor_interaction(self):
        """Test behavior with multiple simultaneous stressors."""
        # Single stressor
        csi_single = calculate_mcsi(80, 0, 0, 0)
        
        # Multiple stressors (compound effect)
        csi_multiple = calculate_mcsi(80, 60, 50, 40)
        
        assert csi_multiple > csi_single, \
            "Multiple stressors should result in higher overall stress"
