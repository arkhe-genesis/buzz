import Mathlib.Data.Real.Basic
import Mathlib.Order.MinMax
import Mathlib.Tactic.Ring
import Mathlib.Tactic.Linarith
import Mathlib.Tactic.Positivity
import Mathlib.Analysis.SpecialFunctions.Pow.Real

/-!
  Cathedral Arkhe — Application: Color Accessibility (WCAG)
-/

namespace CathedralArkhe.UI

def weightR : ℝ := 0.2126
def weightG : ℝ := 0.7152
def weightB : ℝ := 0.0722

@[simp] lemma weights_sum_to_one : weightR + weightG + weightB = 1 := by
  unfold weightR weightG weightB
  norm_num

noncomputable def srgbLinearize (c : ℝ) : ℝ :=
  if c ≤ 0.04045 then c / 12.92 else ((c + 0.055) / 1.055) ^ (12/5 : ℝ)

noncomputable def relativeLuminance (R G B : ℝ) : ℝ :=
  weightR * srgbLinearize R + weightG * srgbLinearize G + weightB * srgbLinearize B

noncomputable def contrastRatio (L1 L2 : ℝ) : ℝ :=
  (max L1 L2 + 0.05) / (min L1 L2 + 0.05)

lemma luminance_nonneg (R G B : ℝ) (hR : 0 ≤ R) (hG : 0 ≤ G) (hB : 0 ≤ B) (hsrgb : ∀ c, 0 ≤ c → 0 ≤ srgbLinearize c) :
  0 ≤ relativeLuminance R G B := by
  unfold relativeLuminance
  apply add_nonneg
  · apply add_nonneg
    · unfold weightR
      exact mul_nonneg (by norm_num) (hsrgb R hR)
    · unfold weightG
      exact mul_nonneg (by norm_num) (hsrgb G hG)
  · unfold weightB
    exact mul_nonneg (by norm_num) (hsrgb B hB)

theorem contrastRatio_symm (L1 L2 : ℝ) :
    contrastRatio L1 L2 = contrastRatio L2 L1 := by
  unfold contrastRatio
  congr 1
  · rw [max_comm]
  · rw [min_comm]

theorem contrastRatio_ge_one (L1 L2 : ℝ) (h1 : 0 ≤ L1) (h2 : 0 ≤ L2) :
    contrastRatio L1 L2 ≥ 1 := by
  unfold contrastRatio
  have h_min_nonneg : 0 ≤ min L1 L2 := by
    exact le_min h1 h2
  have h_min_pos : 0 < min L1 L2 + (0.05 : ℝ) := by linarith
  have h_num_ge_den : max L1 L2 + (0.05 : ℝ) ≥ min L1 L2 + (0.05 : ℝ) := by
    have h3 : min L1 L2 ≤ max L1 L2 := by
      calc
        min L1 L2 ≤ L1 := min_le_left L1 L2
        _ ≤ max L1 L2 := le_max_left L1 L2
    linarith
  exact one_le_div h_min_pos |>.mpr h_num_ge_den

abbrev RGB := Fin 3 → ℝ

def daltonizeProtan (rgb : RGB) : RGB := fun i =>
  if i = 0 then rgb 0 * 0.7 + rgb 1 * 0.3
  else if i = 1 then rgb 1
  else rgb 2

def daltonizeDeutan (rgb : RGB) : RGB := fun i =>
  if i = 0 then rgb 0
  else if i = 1 then rgb 1 * 0.7 + rgb 0 * 0.3
  else rgb 2

def daltonizeTritan (rgb : RGB) : RGB := fun i =>
  if i = 0 then rgb 0
  else if i = 1 then rgb 1
  else rgb 2 * 0.7 + rgb 1 * 0.3

theorem daltonize_preserves_nonneg (type : String) (R G B : ℝ)
    (hR : 0 ≤ R) (hG : 0 ≤ G) (hB : 0 ≤ B) :
    let rgb' := match type with
      | "protan" => daltonizeProtan (fun i => if i = 0 then R else if i = 1 then G else B)
      | "deutan" => daltonizeDeutan (fun i => if i = 0 then R else if i = 1 then G else B)
      | "tritan" => daltonizeTritan (fun i => if i = 0 then R else if i = 1 then G else B)
      | _ => (fun i => if i = 0 then R else if i = 1 then G else B)
    0 ≤ rgb' 0 ∧ 0 ≤ rgb' 1 ∧ 0 ≤ rgb' 2 := by
  split
  · next h =>
    unfold daltonizeProtan
    dsimp
    constructor
    · linarith
    · constructor
      · exact hG
      · exact hB
  · next h =>
    unfold daltonizeDeutan
    dsimp
    constructor
    · exact hR
    · constructor
      · linarith
      · exact hB
  · next h =>
    unfold daltonizeTritan
    dsimp
    constructor
    · exact hR
    · constructor
      · exact hG
      · linarith
  · next h =>
    dsimp
    constructor
    · exact hR
    · constructor
      · exact hG
      · exact hB

def jsTestHarness : Prop := True

end CathedralArkhe.UI
