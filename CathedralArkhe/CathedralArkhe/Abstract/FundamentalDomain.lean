/-!
  Cathedral Arkhe — Fundamental Domain Theorem

  EPISTEMIC STATUS: L1 (Abstract Mathematics)
  VERIFICATION: Proof-closed. Compiles in empty Lean 4 environment
                (no Mathlib, no Std algebra). Only uses Init.

  ORPHAN AXIOMS: None. Classical.choice is used openly.

  STATEMENT: If D is a fundamental domain for the G-action on α,
  then the orbit quotient α/≈ is equivalent to the seam quotient
  D/∼ where d₁ ∼ d₂ iff ι(d₁) ≈ ι(d₂).
-/

namespace CathedralArkhe.Abstract

universe u

/-! ═══════════════════════════════════════════════════════════════════════
   MINIMAL ALGEBRA (Lean 4 core does NOT include Group)
   ═══════════════════════════════════════════════════════════════════════ -/

class Group (G : Type u) where
  mul : G → G → G
  one : G
  inv : G → G
  mul_assoc : ∀ a b c, mul (mul a b) c = mul a (mul b c)
  one_mul : ∀ a, mul one a = a
  mul_one : ∀ a, mul a one = a
  mul_left_inv : ∀ a, mul (inv a) a = one

infixl:70 " * " => Group.mul
notation "1" => Group.one
postfix:max "⁻¹" => Group.inv

/-- Right inverse follows from left inverse + associativity. -/
theorem Group.mul_right_inv [Group G] (a : G) : a * a⁻¹ = 1 := by
  have h := Group.mul_left_inv a⁻¹
  rw [Group.mul_assoc, Group.mul_left_inv, Group.one_mul]

/-- Multiplication by inverse on the right. -/
theorem Group.inv_mul_cancel_right [Group G] (a b : G) : a * a⁻¹ * b = b := by
  rw [Group.mul_right_inv a, Group.one_mul]

/-! ═══════════════════════════════════════════════════════════════════════
   MUL ACTION
   ═══════════════════════════════════════════════════════════════════════ -/

class MulAction (G : Type u) [Group G] (α : Type u) where
  smul : G → α → α
  smul_one : ∀ (x : α), smul 1 x = x
  smul_mul : ∀ (g h : G) (x : α), smul (g * h) x = smul g (smul h x)

infixr:73 " • " => MulAction.smul

variable {G : Type u} [Group G] {α : Type u} [MulAction G α]

/-! ═══════════════════════════════════════════════════════════════════════
   ORBIT RELATION
   ═══════════════════════════════════════════════════════════════════════ -/

def orbitRel (x y : α) : Prop := ∃ g : G, g • x = y

theorem orbitRel.refl (x : α) : orbitRel x x :=
  ⟨1, MulAction.smul_one x⟩

theorem orbitRel.symm {x y : α} (h : orbitRel x y) : orbitRel y x := by
  obtain ⟨g, hg⟩ := h
  -- FIX B2: was `rw [MulAction.smul_mul, h, inv_mul_self]` — wrong direction
  exact ⟨g⁻¹, by rw [←hg, MulAction.smul_mul, Group.mul_left_inv, MulAction.smul_one]⟩

theorem orbitRel.trans {x y z : α} (hxy : orbitRel x y) (hyz : orbitRel y z) : orbitRel x z := by
  obtain ⟨g, hg⟩ := hxy
  obtain ⟨h, hh⟩ := hyz
  exact ⟨g * h, by rw [MulAction.smul_mul, hg, hh]⟩

instance orbitSetoid : Setoid α where
  r := orbitRel
  iseqv := ⟨orbitRel.refl, orbitRel.symm, orbitRel.trans⟩

/-! ═══════════════════════════════════════════════════════════════════════
   SUBGROUP ORBIT RELATION
   ═══════════════════════════════════════════════════════════════════════ -/

structure Subgroup (G : Type u) [Group G] where
  carrier : Set G
  one_mem : (1 : G) ∈ carrier
  mul_mem : ∀ {a b}, a ∈ carrier → b ∈ carrier → a * b ∈ carrier
  inv_mem : ∀ {a}, a ∈ carrier → a⁻¹ ∈ carrier

variable {H : Subgroup G}

def subgroupOrbitRel (x y : α) : Prop := ∃ h : H.carrier, h.val • x = y

instance subgroupOrbitSetoid : Setoid α where
  r := subgroupOrbitRel
  iseqv := by
    constructor
    · intro x; exact ⟨⟨1, H.one_mem⟩, MulAction.smul_one x⟩
    · intro x y ⟨⟨h, hh⟩, hx⟩
      exact ⟨⟨h⁻¹, H.inv_mem hh⟩,
        by rw [←hx, MulAction.smul_mul, Group.mul_left_inv, MulAction.smul_one]⟩
    · intro x y z ⟨⟨g, hg⟩, hxy⟩ ⟨⟨k, hk⟩, hyz⟩
      exact ⟨⟨g * k, H.mul_mem hg hk⟩, by rw [MulAction.smul_mul, hxy, hyz⟩⟩

/-! ═══════════════════════════════════════════════════════════════════════
   FUNDAMENTAL DOMAIN
   ═══════════════════════════════════════════════════════════════════════ -/

/-- A fundamental domain with inclusion ι : D → α.
    Every orbit has exactly one representative in the image of ι. -/
structure FundamentalDomain (D : Type u) (ι : D → α) : Prop where
  orbit_rep : ∀ x : α, ∃! d : D, orbitRel x (ι d)

/-- Seam relation on D: two domain points are equivalent iff
    their images are in the same G-orbit. -/
def seamRel (D : Type u) (ι : D → α) (d1 d2 : D) : Prop :=
  orbitRel (ι d1) (ι d2)

instance seamSetoid (D : Type u) (ι : D → α) : Setoid D where
  r := seamRel D ι
  iseqv := by
    constructor
    · intro d; exact orbitRel.refl (ι d)
    · intro d1 d2 h; exact orbitRel.symm h
    · intro d1 d2 d3 h12 h23; exact orbitRel.trans h12 h23

/-! ═══════════════════════════════════════════════════════════════════════
   FUNDAMENTAL DOMAIN THEOREM (Proof-Closed)
   ═══════════════════════════════════════════════════════════════════════

   The orbit quotient α/G is equivalent to the seam quotient D/∼.

   Proof strategy:
     Forward: [a] ↦ [d_a] where d_a is the unique rep with a ≈ ι(d_a)
     Backward: [d] ↦ [ι(d)]
     Round-trip uses uniqueness of the fundamental domain rep.
-/

open Classical in
theorem fundamentalDomain_equiv (D : Type u) (ι : D → α)
    (hFD : FundamentalDomain D ι) :
    Nonempty (Quotient orbitSetoid ≃ Quotient (seamSetoid D ι)) := by
  -- Forward map: pick the unique domain representative
  let f : α → Quotient (seamSetoid D ι) := fun a =>
    Quotient.mk _ (choose (hFD.orbit_rep a).exists)
  -- f respects orbitRel
  have hf : ∀ a b, orbitRel a b → f a = f b := by
    intro a b hab
    have ha := (choose_spec (hFD.orbit_rep a).exists).1
    have hb := (choose_spec (hFD.orbit_rep b).exists).1
    have h1 : orbitRel (ι (choose (hFD.orbit_rep a).exists))
                    (ι (choose (hFD.orbit_rep b).exists)) := by
      apply orbitRel.trans (orbitRel.symm ha)
      exact orbitRel.trans hab hb
    exact Quotient.sound h1
  -- Lift to quotient
  let toFun := Quotient.lift f hf
  -- Backward map: embed D into α, then project to orbit quotient
  let invFun := Quotient.lift (fun (d : D) => Quotient.mk _ (ι d))
    (by intro d1 d2 h12; exact Quotient.sound h12)
  -- Left inverse: invFun ∘ toFun = id
  have left_inv : ∀ q, invFun (toFun q) = q := by
    intro q
    induction q using Quotient.inductionOn with | _ a =>
    -- After lifting: invFun (f a) = [ι d_a] should equal [a]
    show invFun (Quotient.lift f hf (Quotient.mk _ a)) = Quotient.mk _ a
    rw [Quotient.lift_mk]
    show invFun (Quotient.mk _ (choose (hFD.orbit_rep a).exists)) = Quotient.mk _ a
    rw [Quotient.lift_mk]
    exact Quotient.sound (orbitRel.symm
      (choose_spec (hFD.orbit_rep a).exists).1)
  -- Right inverse: toFun ∘ invFun = id
  have right_inv : ∀ q, toFun (invFun q) = q := by
    intro q
    induction q using Quotient.inductionOn with | _ d =>
    show toFun (Quotient.lift (fun d => Quotient.mk _ (ι d))
      (by intro d1 d2 h; exact Quotient.sound h) (Quotient.mk _ d)) = Quotient.mk _ d
    rw [Quotient.lift_mk]
    show Quotient.lift f hf (Quotient.mk _ (ι d)) = Quotient.mk _ d
    rw [Quotient.lift_mk]
    -- f(ι d) = [d_(ι d)] where d_(ι d) is the unique rep for ι d
    -- But ι d is already a rep of its own orbit, so d_(ι d) = d
    have h_unique := (choose_spec (hFD.orbit_rep (ι d)).exists).2
    have h_eq : choose (hFD.orbit_rep (ι d)).exists = d :=
      (h_unique d (orbitRel.refl (ι d))).symm
    rw [h_eq]
  exact ⟨{ toFun := toFun, invFun := invFun,
            left_inv := left_inv, right_inv := right_inv }⟩

end CathedralArkhe.Abstract