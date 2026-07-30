import Mathlib.Data.Real.Basic
import Mathlib.Tactic.Linarith
import Mathlib.Tactic.Ring

/-!
  Cathedral Arkhe — Application: Responsive Layout
-/

namespace CathedralArkhe.UI.Layout

noncomputable def clamp (x min max : ℝ) : ℝ :=
  if x < min then min
  else if x > max then max
  else x

theorem clamp_within_bounds (x min max : ℝ) (h_min : min ≤ max) :
    min ≤ clamp x min max ∧ clamp x min max ≤ max := by
  unfold clamp
  split_ifs with h1 h2
  · exact ⟨le_rfl, h_min⟩
  · exact ⟨h_min, le_rfl⟩
  · push Not at h1 h2
    exact ⟨h1, h2⟩

theorem clamp_idempotent (x min max : ℝ) (h_min : min ≤ max) :
    clamp (clamp x min max) min max = clamp x min max := by
  unfold clamp
  split_ifs with h1 h2 h3 h4 h5 h6
  · rfl
  · exfalso; linarith
  · rfl
  · exfalso; linarith
  · rfl
  · rfl
  · rfl

noncomputable def fluidValue (vp minVp maxVp minVal maxVal : ℝ) : ℝ :=
  if vp ≤ minVp then minVal
  else if vp ≥ maxVp then maxVal
  else minVal + (maxVal - minVal) * (vp - minVp) / (maxVp - minVp)

theorem fluidValue_monotonic (vp1 vp2 : ℝ) (h : vp1 ≤ vp2)
    (minVp maxVp minVal maxVal : ℝ) (_h_minVp : minVp < maxVp) (h_minVal : minVal ≤ maxVal) :
    fluidValue vp1 minVp maxVp minVal maxVal ≤
    fluidValue vp2 minVp maxVp minVal maxVal := by
  unfold fluidValue
  split_ifs with h1 h2 h3 h4 h5 h6 h7 h8
  · rfl
  · assumption
  · have h_pos : 0 < maxVp - minVp := by linarith
    have h_diff_nonneg : 0 ≤ maxVal - minVal := by linarith
    have h_diff_vp_nonneg : 0 ≤ vp2 - minVp := by linarith
    apply le_add_of_nonneg_right
    apply div_nonneg
    · exact mul_nonneg h_diff_nonneg h_diff_vp_nonneg
    · exact le_of_lt h_pos
  · exfalso; linarith
  · rfl
  · exfalso; linarith
  · exfalso; linarith
  · have h_pos : 0 < maxVp - minVp := by linarith
    have h_diff_nonneg : 0 ≤ maxVal - minVal := by linarith
    have h_diff_vp_nonneg : 0 ≤ vp1 - minVp := by linarith
    have h_le_1 : minVal + (maxVal - minVal) * (vp1 - minVp) / (maxVp - minVp) ≤ minVal + (maxVal - minVal) * (maxVp - minVp) / (maxVp - minVp) := by
      apply add_le_add_right
      apply div_le_div_of_nonneg_right
      · apply mul_le_mul_of_nonneg_left
        · linarith
        · exact h_diff_nonneg
      · exact le_of_lt h_pos
    have h_eq : minVal + (maxVal - minVal) * (maxVp - minVp) / (maxVp - minVp) = maxVal := by
      rw [mul_div_cancel_right₀ _ (ne_of_gt h_pos)]
      ring
    linarith
  · have h_pos : 0 < maxVp - minVp := by linarith
    have h_diff_nonneg : 0 ≤ maxVal - minVal := by linarith
    apply add_le_add_right
    apply div_le_div_of_nonneg_right
    · apply mul_le_mul_of_nonneg_left
      · linarith
      · exact h_diff_nonneg
    · exact le_of_lt h_pos

noncomputable def columnWidth (containerWidth : ℝ) (nCols : ℕ) (gap : ℝ) : ℝ :=
  (containerWidth - (nCols - 1) * gap) / nCols

theorem columnWidth_nonneg (containerWidth : ℝ) (nCols : ℕ) (gap : ℝ)
    (h : containerWidth ≥ (nCols - 1) * gap) :
    columnWidth containerWidth nCols gap ≥ 0 := by
  unfold columnWidth
  apply div_nonneg
  · linarith
  · exact Nat.cast_nonneg nCols

end CathedralArkhe.UI.Layout
