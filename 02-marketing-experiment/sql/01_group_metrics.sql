-- One row per randomized customer; all zero-outcome customers remain in denominator.
SELECT segment, COUNT(*) AS customers,
       SUM(visit) visitors, AVG(visit) visit_rate,
       SUM(conversion) purchasers, AVG(conversion) conversion_rate,
       SUM(spend) revenue, AVG(spend) revenue_per_assigned_customer,
       VAR_SAMP(spend) spend_variance,
       AVG(CASE WHEN conversion=1 THEN spend END) spend_per_buyer_descriptive_only
FROM customers GROUP BY segment ORDER BY segment;
