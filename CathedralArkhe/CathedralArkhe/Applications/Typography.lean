import Mathlib.Data.Real.Basic
import Mathlib.Tactic.Linarith
import Mathlib.Tactic.Ring
import Mathlib.Analysis.SpecialFunctions.Pow.Real

/-!
  Cathedral Arkhe — Application: Modular Typography Scales
-/

namespace CathedralArkhe.UI.Typography

noncomputable def goldenRatio : ℝ := (1 + Real.sqrt 5) / 2

theorem golden_ratio_square : goldenRatio * goldenRatio = goldenRatio + 1 := by
  unfold goldenRatio
  have h1 : (Real.sqrt 5) ^ 2 = 5 := Real.sq_sqrt (by linarith)
  have h2 : (Real.sqrt 5) * (Real.sqrt 5) = 5 := by
    calc
      (Real.sqrt 5) * (Real.sqrt 5) = (Real.sqrt 5) ^ 2 := by ring
      _ = 5 := h1
  calc
    ((1 + Real.sqrt 5) / 2) * ((1 + Real.sqrt 5) / 2) = (1 + 2 * Real.sqrt 5 + (Real.sqrt 5) * (Real.sqrt 5)) / 4 := by ring
    _ = (1 + 2 * Real.sqrt 5 + 5) / 4 := by rw [h2]
    _ = (6 + 2 * Real.sqrt 5) / 4 := by ring
    _ = (3 + Real.sqrt 5) / 2 := by ring
    _ = ((1 + Real.sqrt 5) / 2) + 1 := by ring

theorem golden_ratio_pos : 0 < goldenRatio := by
  unfold goldenRatio
  have h1 : 0 ≤ (5 : ℝ) := by linarith
  have h2 : 0 ≤ Real.sqrt 5 := Real.sqrt_nonneg 5
  linarith

noncomputable def geometricScale (base : ℝ) (ratio : ℝ) (n : ℕ) : ℝ :=
  base * ratio ^ n

theorem geometricScale_monotone (base : ℝ) (ratio : ℝ) (h_ratio : 1 ≤ ratio) (h_base : 0 ≤ base)
    (n m : ℕ) (h_le : n ≤ m) :
    geometricScale base ratio n ≤ geometricScale base ratio m := by
  unfold geometricScale
  have h_ratio_nonneg : 0 ≤ ratio := by linarith
  have h_pow_le : ratio ^ n ≤ ratio ^ m := pow_le_pow_right₀ h_ratio h_le
  exact mul_le_mul_of_nonneg_left h_pow_le h_base

noncomputable def perfectFourth : ℝ := 4 / 3
noncomputable def perfectFifth : ℝ := 3 / 2

theorem fourth_less_fifth : perfectFourth < perfectFifth := by
  unfold perfectFourth perfectFifth
  norm_num

noncomputable def pythagoreanScale (base : ℝ) (n : ℕ) : ℝ :=
  base * (3 / 2 : ℝ) ^ n

noncomputable def equalTemperament (base : ℝ) (n : ℕ) : ℝ :=
  base * (2 : ℝ) ^ (n / 12 : ℝ)

theorem equalTemperament_exponential (base : ℝ) (n m : ℕ) :
    equalTemperament base (n + m) = equalTemperament base n * (2 : ℝ) ^ (m / 12 : ℝ) := by
  unfold equalTemperament
  have h_add : ((n + m : ℕ) : ℝ) / 12 = (n : ℝ) / 12 + (m : ℝ) / 12 := by
    push_cast
    ring
  rw [h_add]
  rw [Real.rpow_add (by linarith)]
  ring

end CathedralArkhe.UI.Typography
