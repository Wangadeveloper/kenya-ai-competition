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

    def create_farmer_node(self, user_id, name, phone_number, county, main_crop=None, cooperative=None):
        """
        Creates or updates a unified User node within the graph database network, 
        mapping structural attributes like location and cooperative membership.
        """
        with self.driver.session() as session:
            query = """
            MERGE (u:User {phone_number: $phone_number})
            SET u.user_id = $user_id, u.full_name = $name, u.county = $county, u.role = 'farmer'
            WITH u
            WHERE $main_crop IS NOT NULL AND $main_crop <> ''
                MERGE (c:Crop {name: $main_crop})
                MERGE (u)-[:GROWS]->(c)
            WITH u
            WHERE $cooperative IS NOT NULL AND $cooperative <> ''
                MERGE (coop:Cooperative {name: $cooperative})
                MERGE (u)-[:MEMBER_OF]->(coop)
            """
            session.run(
                query, 
                user_id=user_id, 
                name=name, 
                phone_number=phone_number, 
                county=county, 
                main_crop=main_crop, 
                cooperative=cooperative
            )

    def get_similar_farmers(self, county, main_crop, exclude_phone):
        """
        Traverses crop nodes to locate localized smallholders sharing 
        similar agricultural patterns for peer advisory rendering.
        """
        with self.driver.session() as session:
            query = """
            MATCH (u:User {role: 'farmer'})-[:GROWS]->(c:Crop {name: $main_crop})
            WHERE u.county = $county AND u.phone_number <> $exclude_phone
            RETURN u.full_name AS name, u.county AS county, c.name AS crop 
            LIMIT 3
            """
            result = session.run(query, county=county, main_crop=main_crop, exclude_phone=exclude_phone)
            return [record.data() for record in result]

    def create_subscription_relationship(self, subscriber_phone, subscriber_name, farmer_phone, channel='SMS'):
        """
        Creates a directed SUBSCRIBED_TO network edge tracking user broadcast profiles.
        """
        with self.driver.session() as session:
            query = """
            MERGE (subscriber:User {phone_number: $subscriber_phone})
            SET subscriber.full_name = $subscriber_name
            MERGE (farmer:User {phone_number: $farmer_phone})
            MERGE (subscriber)-[r:SUBSCRIBED_TO]->(farmer)
            SET r.channel = $channel
            """
            session.run(
                query, 
                subscriber_phone=subscriber_phone, 
                subscriber_name=subscriber_name, 
                farmer_phone=farmer_phone, 
                channel=channel
            )

    def get_market_buyers(self, crop_name):
        """
        Finds open market buyers registered to purchase harvested assets.
        """
        with self.driver.session() as session:
            query = """
            MATCH (b:Buyer)-[:BUYS]->(c:Crop {name: $crop_name})
            RETURN b.name AS name, b.contact AS contact, b.location AS location
            """
            result = session.run(query, crop_name=crop_name)
            return [record.data() for record in result]