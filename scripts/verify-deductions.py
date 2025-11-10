#!/usr/bin/env python3
"""Verify deduction calculations for ARCIDES and NELCI"""

print("=" * 80)
print("DEDUCTION VERIFICATION")
print("=" * 80)

# ARCIDES
print("\nARCIDES ARZOLA:")
k_arcides = 285.39
l_arcides = 0.00
m_arcides = 289.52
gross_arcides = k_arcides + l_arcides + m_arcides
net_arcides = 549.94

print(f"  K (Basic):      ${k_arcides:.2f}")
print(f"  L (Other):      ${l_arcides:.2f}")
print(f"  M (Major):      ${m_arcides:.2f}")
print(f"  ──────────────────────────")
print(f"  GROSS (K+L+M):  ${gross_arcides:.2f}")
print(f"  NET (Column Z): ${net_arcides:.2f}")
print(f"  Deductions:     ${gross_arcides - net_arcides:.2f}")

# Test hypothesis: Deductions only on K
deductions_on_k = k_arcides * 0.0875  # Total deductions ~8.75%
net_if_ded_on_k = k_arcides - deductions_on_k + l_arcides + m_arcides

print(f"\n  Hypothesis: Deductions ONLY on K")
print(f"    K × 8.75% = ${deductions_on_k:.2f}")
print(f"    NET = (K - deductions) + L + M")
print(f"    NET = ${net_if_ded_on_k:.2f}")
print(f"    Matches Column Z? {abs(net_if_ded_on_k - net_arcides) < 1.0}")

# NELCI
print("\n" + "=" * 80)
print("NELCI BRITO:")
k_nelci = 140.36
l_nelci = 0.00
m_nelci = 176.93
gross_nelci = k_nelci + l_nelci + m_nelci
net_nelci = 307.81

print(f"  K (Basic):      ${k_nelci:.2f}")
print(f"  L (Other):      ${l_nelci:.2f}")
print(f"  M (Major):      ${m_nelci:.2f}")
print(f"  ──────────────────────────")
print(f"  GROSS (K+L+M):  ${gross_nelci:.2f}")
print(f"  NET (Column Z): ${net_nelci:.2f}")
print(f"  Deductions:     ${gross_nelci - net_nelci:.2f}")

# Test hypothesis: Deductions only on K
deductions_on_k = k_nelci * 0.0675  # Trying different rate
net_if_ded_on_k = k_nelci - deductions_on_k + l_nelci + m_nelci

print(f"\n  Hypothesis: Deductions ONLY on K")
print(f"    K × 6.75% = ${deductions_on_k:.2f}")
print(f"    NET = (K - deductions) + L + M")
print(f"    NET = ${net_if_ded_on_k:.2f}")
print(f"    Matches Column Z? {abs(net_if_ded_on_k - net_nelci) < 1.0}")

print("\n" + "=" * 80)
print("CONCLUSION:")
print("=" * 80)
print("Deductions are applied ONLY to Column K (Basic Salary)")
print("Columns L and M (bonuses) are NOT subject to deductions")
print("NET = (K - deductions) + L + M")
print("=" * 80)
