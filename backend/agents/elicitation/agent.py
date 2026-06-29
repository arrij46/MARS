import asyncio
import json
from agents.base_agent import BaseAgent
from agents.elicitation.chatbot import ImprovedRequirementsElicitation
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from orchestrator.shared_state import get_shared_state
import os

class ElicitationAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="Elicitation", exchange="agents-exchange", queue="Elicitation")
        self.ORCHESTRATOR_QUEUE = "Orchestrator"
        self.chatbot = ImprovedRequirementsElicitation()

    async def handle_message(self, msg: dict):
        """Handle incoming A2A message"""
        conv_id = msg.get("conv_id", "unknown")
        msg_type = msg.get("type", "")
        
        print(f"[{self.name}] Received message: {msg_type}")
        
        if msg_type == "start_elicitation":
            # Start the elicitation process
            print(f"[{self.name}] Starting requirement elicitation process...")
            # await self.run_elicitation_session(conv_id)
        else:
            print(f"[{self.name}] Unknown message type: {msg_type}")

    async def run_elicitation_session(self, conv_id: str):
        """Run the interactive elicitation session with the user"""
        print("\n" + "="*50)
        print(" Requirement Elicitation Session Started")
        print("="*50)
        
        # Phase 1: Collect project title and description
        await self.collect_project_info()
        
        # Phase 2: Interactive requirement gathering
        await self.interactive_requirement_gathering(conv_id)
        
        # Phase 3: Generate structured document
        doc_path = await self.generate_requirements_document()
        
        # Phase 4: Send results back to orchestrator
        await self.send_results_to_orchestrator(conv_id, doc_path)

    async def collect_project_info(self):
        """Collect project title and description from user"""
        print("\n Project Information Collection")
        print("-" * 50)
        
        # Get project title
        while not self.project_title:
            self.project_title = input("\n Enter Project Title: ").strip()
            if not self.project_title:
                print(" Project title cannot be empty. Please try again.")
        
        # Get project description
        while not self.project_description:
            self.project_description = input("\n Enter Project Description (can be multiple lines, press Enter twice when done):\n").strip()
            
            # Allow multi-line input
            lines = [self.project_description]
            while True:
                line = input()
                if line.strip() == "":
                    break
                lines.append(line)
            
            self.project_description = "\n".join(lines).strip()
            
            if not self.project_description:
                print(" Project description cannot be empty. Please try again.")
        
        print(f"\n✅ Project Info Collected:")
        print(f"   Title: {self.project_title}")
        print(f"   Description: {self.project_description[:100]}...")

    async def interactive_requirement_gathering(self, conv_id):
        """Run interactive chatbot session to gather requirements"""
        print("\n" + "="*50)
        print("💬 Interactive Requirement Gathering")
        print("="*50)
        print("I will help you clarify requirements for your software system.")
        print("Type 'done' when you've finished describing all requirements.")
        print("Type 'quit' to exit without saving.")
        print("="*50)
        
        self.conversation_active = True
        
        while self.conversation_active:
            try:
                user_input = input("\n🧑 You: ").strip()
                
                if user_input.lower() in ['done', 'finished', 'complete']:
                    if len(self.requirements_list) > 0:
                        print(f"\n✅ Requirement gathering completed. Collected {len(self.requirements_list)} requirements.")
                        self.conversation_active = False
                        break
                    else:
                        print(" No requirements collected yet. Please describe at least one requirement or type 'quit' to exit.")
                        continue
                
                if user_input.lower() in ['quit', 'exit', 'bye']:
                    confirm = input("⚠️  Are you sure you want to quit without saving? (yes/no): ").lower()
                    if confirm == 'yes':
                        print("\n Session cancelled.")
                        self.conversation_active = False
                        self.requirements_list = []
                        return
                    else:
                        continue
                
                if not user_input:
                    continue
                        
                shared_state = get_shared_state()
                conv = shared_state.get_conversation(conv_id)
                project_title = conv.get("metadata", {}).get("title", "Untitled Project")
                project_description = shared_state.get_project_description(conv_id) or "No project description available."
                form_info = {
                            "project_title":project_title,
                            "project_description":project_description
                        }

                # Get response from chatbot
                print(" Bot: ", end="")
                response = self.chatbot.chat(user_input, form_info)
                print(response)
                
                # Extract requirements from successful interactions
                if self._is_valid_requirement(user_input, response):
                    self.requirements_list.append(user_input)
                
            except KeyboardInterrupt:
                print("\n\n⚠️  Session interrupted.")
                confirm = input("Save collected requirements? (yes/no): ").lower()
                if confirm != 'yes':
                    self.requirements_list = []
                self.conversation_active = False
                break
            except Exception as e:
                print(f"\n Error: {e}")

    def _is_valid_requirement(self, user_input: str, bot_response: str) -> bool:
        """Check if the user input represents a valid requirement"""
        # Don't save if bot rejected the input
        rejection_phrases = [
            "I focus on realistic software systems",
            "I am a requirement gathering expert, I can only help with software requirements",
            "Please describe a practical software project"
        ]
        
        for phrase in rejection_phrases:
            if phrase in bot_response:
                return False
        
        # Don't save questions or commands
        command_words = ['summarize', 'summary', 'can you', 'what', 'how', 'why', 'help']
        if any(word in user_input.lower() for word in command_words):
            return False
        
        # Don't save very short inputs
        if len(user_input.split()) < 3:
            return False
        
        return True

    async def generate_requirements_document(self) -> str:
        """Generate a structured .docx document with requirements"""
        print("\n📄 Generating requirements document...")
        
        # Create document
        doc = Document()
        
        # Add title
        title = doc.add_heading(self.project_title, 0)
        title.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
        
        # Add summary section
        doc.add_heading('Summary', 1)
        summary_para = doc.add_paragraph(self.project_description)
        summary_para.style = 'Normal'
        
        # Add system requirements section
        doc.add_heading('System Requirements', 1)
        
        if self.requirements_list:
            for idx, req in enumerate(self.requirements_list, 1):
                # Add requirement as bullet point
                para = doc.add_paragraph(f"The system shall {req}", style='List Bullet')
                para.style.font.size = Pt(11)
        else:
            doc.add_paragraph("No requirements collected during this session.", style='Normal')
        
        # Save document
        filename = f"{self.project_title.replace(' ', '_')}_Requirements.docx"
        filepath = os.path.join(os.getcwd(), filename)
        doc.save(filepath)
        
        print(f"✅ Document saved: {filepath}")
        return filepath

    async def send_results_to_orchestrator(self, conv_id: str, doc_path: str):
        """Send the elicitation results back to orchestrator"""
        print(f"\n[{self.name}] Sending results to Orchestrator...")
        
        payload = {
            "status": "done",
            "from": self.name,
            "project_title": self.project_title,
            "project_description": self.project_description,
            "requirements_count": len(self.requirements_list),
            "requirements": self.requirements_list,
            "document_path": doc_path
        }
        
        await self.send_message(
            receiver="Orchestrator",
            payload=payload,
            type_="elicitation_complete",
            conv_id=conv_id
        )
        
        print(f"[{self.name}] ✅ Elicitation completed and results sent to Orchestrator")

    async def start_agent(self):
        """Start the agent and listen for messages"""
        print(f"[{self.name}] Agent started and listening on queue '{self.queue}'")
        await self.message_broker.consume_queue(self.queue, self.handle_message)

    def start_session(self, conv_id: str):
        """Start a new elicitation session (sync; called from FastAPI routes)."""
        self.conv_id = conv_id

    async def collect_baseline_info(self, conv_id: str, baseline_text: str):
        """Collect baseline system information"""
        self.conv_id = conv_id
        shared_state = get_shared_state()
        # Get Project description from shared state
        project_description = shared_state.get_project_description(conv_id) or "No project description available."

        conv = shared_state.get_conversation(conv_id)
        project_title = conv.get("metadata", {}).get("title", "Untitled Project")
        return await self.chatbot.collect_baseline(conv_id, baseline_text)

    async def chat_message(self, conv_id: str, message: str):
        """Handle a chat message"""
        shared_state = get_shared_state()
        conv = shared_state.get_conversation(conv_id)

        project_title = conv.get("metadata", {}).get("title", "Untitled Project")
        project_description = shared_state.get_project_description(conv_id) or "No project description available."
        form_info = {
                    "project_title":project_title,
                    "project_description":project_description
                }
        conv = shared_state.get_conversation(conv_id)
        return await self.chatbot.chat(conv_id, message, form_info) # Pass conv_id here!

    async def end_session(self, conv_id: str):
        """End the elicitation session"""
        return await self.chatbot.end_elicitation(conv_id)

    def delete_requirement(self, conv_id: str, index: int):
        """Proxy method to delete a requirement via the chatbot"""
        return self.chatbot.delete_requirement(conv_id, index)

    def edit_requirement(self, conv_id: str, index: int, new_text: str):
        """Proxy method to edit a requirement via the chatbot"""
        return self.chatbot.edit_requirement(conv_id, index, new_text)
    
if __name__ == "__main__":
    agent = ElicitationAgent()
    asyncio.run(agent.start_agent())