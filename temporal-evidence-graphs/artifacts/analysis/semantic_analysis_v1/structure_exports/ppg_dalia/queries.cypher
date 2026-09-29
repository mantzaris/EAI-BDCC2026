// nodes
MATCH (n) WHERE n.scope STARTS WITH $prefix RETURN elementId(n) AS id, labels(n) AS labels, properties(n) AS properties ORDER BY n.scope, id;

// edges
MATCH (n)-[r]->(m) WHERE n.scope STARTS WITH $prefix RETURN elementId(r) AS id, elementId(n) AS source, elementId(m) AS target, type(r) AS type, properties(r) AS properties, n.scope AS scope ORDER BY scope, id;

// counts
MATCH (n) WHERE n.scope STARTS WITH $prefix OPTIONAL MATCH (n)-[r]->() RETURN n.scope AS scope, count(DISTINCT n) AS nodes, count(r) AS edges ORDER BY scope;

// paths
MATCH (c:ClaimVersion {scope:$scope})-[:DEPENDS_ON]->(f:FeatureVersion)-[:DERIVED_FROM]->(o:Observation) RETURN c.id AS claim, f.id AS feature, o.id AS observation ORDER BY claim, feature, observation LIMIT 5;
