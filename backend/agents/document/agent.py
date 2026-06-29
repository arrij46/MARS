import asyncio

import httpx
from  agents.base_agent import BaseAgent  
from collections import defaultdict
from agents.document.llm_reasoner import generate_srs
from orchestrator.shared_state import get_shared_state

class DocumentAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="Document", exchange="agents-exchange", queue="Document")
        self.ORCHESTRATOR_QUEUE = "Orchestrator"
        self.requirement_list = []
        self.project_title = ''
        self.project_description=''


    async def handle_message(self, msg: dict):
        """
        # get the functional and non-functional requirements from the db
        # separate them into two lists
        # call the LLM feature extractor to cluster them into features
        # pass the clustered features to the LLM reasoner to generate SRS document
        # save the generated SRS document to the database
        # load the generated SRS document from the database and display on the screen
        """
        print(f"[{self.name}] Hey, I've received my call.")
        self.conv_id = msg.get("conv_id", "unknown")        
        self.project_title = msg.get("payload")["input_doc"]['title']
        self.project_description = msg.get("payload")["input_doc"]['summary']
        self.requirement_list = msg.get("payload")["final_requirement_set"]['cleaned_classified']['requirements']
        self.clustered_fr = msg.get("payload")["clustered_fr"] 
        
        # separate functional and non-functional requirements
        non_functional_reqs = [req for req in self.requirement_list if req['type'] == 'Non-Functional']

        # group nft by subtypes
        grouped_by_subtype = defaultdict(list)
        # groups types of nfrs
        for req in non_functional_reqs:
            grouped_by_subtype[req['subtype']].append(f'{req["id"]}: {req["text"]}')
        # converts the set of lists to dict
        non_functional_reqs = dict(grouped_by_subtype)
        
        print(f'[{self.name}] non functional reqs: ', non_functional_reqs )

        # ──  wait for user to select/create template ──
        print(f"[{self.name}] Waiting for template selection...")

        shared_state = get_shared_state()
        event = shared_state.create_template_ready_event(self.conv_id)


        # wait for the event to be set by the API route when template is ready
        await event.wait()
        print(f"[{self.name}] Template ready, resuming SRS generation")

        # Fetch template via internal API
        template = await self.fetch_template(self.conv_id)

        # send clustered reqs to llm reasoner
        try: 
            srs_doc_json = await generate_srs(
                self.clustered_fr, 
                non_functional_reqs, 
                self.project_title, 
                self.project_description,
                f"./agents/document/results", 
                self.conv_id,
                template=template)
            
            #print(f"[{self.name}]srs doc: ", srs_doc_json )
            print(f"[{self.name}] SRS document generated successfully, now saving to database...")
            try:
                await self.save_to_database(srs_doc_json)
                print(f" SRS saved successfully for project {self.conv_id}")
            except Exception as e:
                print(f'[{self.name}] error in saving srs to database: {e}')

        except Exception as e:
            print(f"[{self.name}] Error in generation srs doc: {e}")

        # Reply back to orchestrator using parent's send_message
        await self.send_message(
            receiver="Orchestrator",
            payload={"status": "done", "from": self.name},
            type_="confirm",
            conv_id=self.conv_id
        )

    async def start_agent(self):
        """Start the agent and listen for messages"""
        print(f"\n{'='*80}")
        print(f"[{self.name}] AGENT STARTING")
        print(f"{'='*80}\n")        
        
        await self.message_broker.consume_queue(self.queue, self.handle_message)


    async def save_to_database(self, srs_json: dict):
        """Call the API route to save SRS"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"http://localhost:8000/api/projects/{self.conv_id}/srs/save",
                json={
                    "srs_json": srs_json,  # Your SRS data
                    "project_description": self.project_description,
                    "project_title": self.project_title
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"Saved with SRS ID: {result['srs_id']}")
            else:
                print(f"Failed to save: {response.text}")

    # ADD this method to the class
    async def fetch_template(self, conv_id: str) -> dict | None:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"http://localhost:8000/api/templates/forProject/{conv_id}"
                )
                if response.status_code == 200:
                    return response.json()
                print(f"[{self.name}] No template found, using default")
                return None
        except Exception as e:
            print(f"[{self.name}] Failed to fetch template: {e}, using default")
            return None


if __name__ == "__main__":
    import asyncio
    agent = DocumentAgent()  # inherits from BaseAgent
    asyncio.run(agent.start_agent())

 