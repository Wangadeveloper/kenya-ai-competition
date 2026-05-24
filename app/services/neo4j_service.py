from neo4j import GraphDatabase
from flask import current_app

class Neo4jService:
    def __init__(self):
        config = current_app.config
        self.driver = GraphDatabase.driver(
            config['NEO4J_URI'], 
            auth=(config['NEO4J_USER'], config['NEO4J_PASSWORD'])
        )

    def close(self):
        self.driver.close()

    def create_farmer_node(self, user_id, name, county, cooperative, main_crop):
        with self.driver.session() as session:
            query = """
            MERGE (f:Farmer {id: $user_id})
            SET f.name = $name, f.county = $county
            WITH f
            MERGE (c:Crop {name: $main_crop})
            MERGE (f)-[:GROWS]->(c)
            WITH f
            IF $cooperative IS NOT NULL AND $cooperative <> ''
                MERGE (coop:Cooperative {name: $cooperative})
                MERGE (f)-[:MEMBER_OF]->(coop)
            END
            """
            session.run(query, user_id=user_id, name=name, county=county, cooperative=cooperative, main_crop=main_crop)

    def get_similar_farmers(self, county, main_crop, exclude_id):
        with self.driver.session() as session:
            # Matches peer nodes sharing the same crop or localized ecosystem attributes
            query = """
            MATCH (f:Farmer)-[:GROWS]->(c:Crop {name: $main_crop})
            WHERE f.county = $county AND f.id <> $exclude_id
            RETURN f.name AS name, f.county AS county, c.name AS crop LIMIT 3
            """
            result = session.run(query, county=county, main_crop=main_crop, exclude_id=exclude_id)
            return [record.data() for record in result]

    def create_follow_relationship(self, follower_id, following_id):
        with self.driver.session() as session:
            query = """
            MATCH (a:Farmer {id: $follower_id}), (b:Farmer {id: $following_id})
            MERGE (a)-[:FOLLOWS]->(b)
            """
            session.run(query, follower_id=follower_id, following_id=following_id)

    def get_market_buyers(self, crop_name):
        with self.driver.session() as session:
            query = """
            MATCH (b:Buyer)-[:BUYS]->(c:Crop {name: $crop_name})
            RETURN b.name AS name, b.contact AS contact, b.location AS location
            """
            result = session.run(query, crop_name=crop_name)
            return [record.data() for record in result]