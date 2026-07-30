import Mathlib.Data.Real.Basic
import Mathlib.Order.Interval.Set.Basic
import Mathlib.Tactic.Linarith

namespace CathedralArkhe.T1
variable (L w : ℝ)

def Rect : Type :=
  { p : ℝ × ℝ // p.1 ∈ Set.Icc 0 L ∧ p.2 ∈ Set.Icc (-(w / 2)) (w / 2) }

def MobiusRel (p q : Rect L w) : Prop :=
  p.val = q.val ∨
  (p.val.fst = 0 ∧ q.val.fst = L ∧ p.val.snd = -q.val.snd) ∨
  (q.val.fst = 0 ∧ p.val.fst = L ∧ q.val.snd = -p.val.snd)

def mobiusSetoid (hL : L > 0) : Setoid (Rect L w) where
  r := MobiusRel L w
  iseqv := by
    refine ⟨fun x => Or.inl rfl, ?_, ?_⟩
    · -- symmetry
      rintro x y (h | ⟨a,b,c⟩ | ⟨a,b,c⟩)
      · exact Or.inl h.symm
      · exact Or.inr (Or.inr ⟨a, b, c⟩)
      · exact Or.inr (Or.inl ⟨a, b, c⟩)
    · -- transitivity
      rintro x y z hxy hyz
      rcases hxy with hxy | hxy | hxy
      · rcases hyz with hyz | hyz | hyz
        · exact Or.inl (hxy.trans hyz)
        · exact Or.inr (Or.inl (by rw [hxy]; exact hyz))
        · exact Or.inr (Or.inr (by rw [hxy]; exact hyz))
      · rcases hyz with hyz | hyz | hyz
        · exact Or.inr (Or.inl (by rw [← hyz]; exact hxy))
        · exfalso
          have h1 : y.val.fst = L := hxy.2.1
          have h2 : y.val.fst = 0 := hyz.1
          linarith
        · refine Or.inl (Prod.ext_iff.mpr ⟨?_, ?_⟩)
          · exact hxy.1.trans hyz.1.symm
          · exact hxy.2.2.trans hyz.2.2.symm
      · rcases hyz with hyz | hyz | hyz
        · exact Or.inr (Or.inr (by rw [← hyz]; exact hxy))
        · refine Or.inl (Prod.ext_iff.mpr ⟨?_, ?_⟩)
          · exact hxy.2.1.trans hyz.2.1.symm
          · exact neg_injective (hxy.2.2.symm.trans hyz.2.2)
        · exfalso
          have h1 : y.val.fst = 0 := hxy.1
          have h2 : y.val.fst = L := hyz.2.1
          linarith

end CathedralArkhe.T1
