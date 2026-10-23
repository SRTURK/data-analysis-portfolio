-- All segments are pre-treatment attributes. mens/womens are purchase flags, not gender.
WITH labeled AS (
 SELECT *, CASE WHEN mens=1 AND womens=1 THEN 'both'
                WHEN mens=1 THEN 'mens_only'
                WHEN womens=1 THEN 'womens_only' ELSE 'neither' END purchase_type
 FROM customers
)
SELECT split, purchase_type, segment, COUNT(*) customers,
       AVG(visit) visit_rate, AVG(conversion) conversion_rate, AVG(spend) revenue_per_customer
FROM labeled GROUP BY split,purchase_type,segment ORDER BY split,purchase_type,segment;
