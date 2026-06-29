import os
import json
import groq
import re
from datetime import datetime

try:
    from langchain.memory import ConversationBufferWindowMemory
except ImportError:
    from langchain_community.chat_message_histories import ChatMessageHistory

    # Simplified memory implementation if langchain.memory not available
    class ConversationBufferWindowMemory:
        def __init__(self, k=10, return_messages=True):
            self.k = k
            self.messages = []
            self.project_title=''
            self.project_description=''

        def save_context(self, inputs, outputs):
            self.messages.append({"input": inputs["input"], "output": outputs["output"]})

            if len(self.messages) > self.k:
                self.messages = self.messages[-self.k:]

        def load_memory_variables(self, inputs):
            class Message:
                def __init__(self, content, msg_type):
                    self.content = content
                    self.type = msg_type

            history = []
            for msg in self.messages:
                history.append(Message(msg["input"], "human"))
                history.append(Message(msg["output"], "ai"))
            return {"history": history}


from dotenv import load_dotenv

load_dotenv()

# Fixed checklist for aspect coverage tracking (_update_covered_aspects); not LLM-generated.
DEFAULT_BASELINE_ASPECTS = [
    "User roles and authentication",
    "Core functionality",
    "Data management",
    "Security requirements",
    "User interface",
]


class ImprovedRequirementsElicitation:
    def __init__(self):
        self.client = groq.Groq(api_key=os.getenv("GROQ_API_KEY_DOCUMENT_ACCOUNT2"))
        self.sessions = {}
        self.conv_id = None
        self.system_baseline = None

        # Enhanced system prompt with EARS principles
        self.system_prompt = """You are an expert Requirements Engineering specialist trained in EARS (Easy Approach to Requirements Syntax) and IEEE standards.

CORE RESPONSIBILITIES:
1. Extract ONLY explicitly stated requirements from user input
2. Ensure requirements are unambiguous, testable, and atomic
3. Ask clarifying questions for vague or ambiguous statements
4. NEVER suggest features or infer requirements not mentioned by the user
5. Validate requirements follow proper structure: subject + action + object

EARS VALIDATION RULES:
- NO vague terms: avoid "user-friendly", "fast", "easy", "intuitive", "flexible"
- ATOMIC: One requirement per statement (no "and", "or" joining multiple requirements)
- MEASURABLE: Specific, quantifiable, or verifiable conditions
- COMPLETE: Clear subject (who), action (what), and object (on what)
- PROPER LANGUAGE: Use "shall" for mandatory requirements

AMBIGUOUS WORDS TO CHALLENGE:
- Quality terms: good, bad, user-friendly, intuitive, easy, efficient
- Quantity terms: many, few, some, several, most
- Time terms: fast, slow, quick, responsive, real-time (without specific values)
- Comparison: better, worse, improved, enhanced (without baseline)

WHEN USER PROVIDES VAGUE INPUT:
- Ask specific questions: "How many users?", "What response time?", "Which user roles?"
- Request concrete examples or scenarios
- Seek measurable criteria

RESPONSE PATTERN:
- Extract requirement: State it clearly on a new line. ALWAYS prefix it with "REQUIREMENT: " so it can be saved exactly word-for-word. Example: "REQUIREMENT: The system shall allow users to log in securely."
- Check for ambiguity: If found, ask clarification
- Confirm with user before storing
- Continue probing for completeness

FORBIDDEN ACTIONS:
- DO NOT suggest features user hasn't mentioned
- DO NOT make assumptions about functionality
- DO NOT infer requirements from partial information
- DO NOT combine multiple requirements into one statement

Give all your outputs in markdown.
"""

    def get_session_file(self, conv_id):
        """Helper to safely get file path from the session-files directory"""
        save_dir = "session-files"
        # Ensure the directory exists
        os.makedirs(save_dir, exist_ok=True)
        return os.path.join(save_dir, f"requirements_session_{conv_id}.json")

    def load_session(self, conv_id):
        """Load previous session if exists"""
        session_file = self.get_session_file(conv_id)
        if os.path.exists(session_file):
            try:
                with open(session_file, 'r') as f:
                    self.sessions[conv_id] = json.load(f)

                    # Initialize memory since it's not serialized
                    if 'memory' not in self.sessions[conv_id] or self.sessions[conv_id]['memory'] is None:
                        self.sessions[conv_id]['memory'] = ConversationBufferWindowMemory(k=10, return_messages=True)

                    # Ensure defaults for loaded data
                    self.sessions[conv_id].setdefault('baseline', None)
                    self.sessions[conv_id].setdefault('requirements_list', [])
                    self.sessions[conv_id].setdefault('baseline_collected', False)
                    self.sessions[conv_id].setdefault('aspects_covered', [])
                    self.sessions[conv_id].setdefault('baseline_aspects', [])

                    return True
            except Exception as e:
                print(f"Could not load previous session: {e}")

        return False


    def save_session(self, conv_id):
        """Save current session to JSON"""
        try:
            data = self.sessions[conv_id]

            # Strip out the non-serializable 'memory' object before dumping
            data_to_save = {k: v for k, v in data.items() if k != 'memory'}
            data_to_save['timestamp'] = datetime.now().isoformat()

            session_file = self.get_session_file(conv_id)
            with open(session_file, 'w') as f:
                json.dump(data_to_save, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save session: {e}")

    import re

    def generate_aspects_and_initial_requirements(self, baseline_summary):
        """Return fixed baseline aspects + up to 20 initial REQ lines from the model (no LLM aspect list)."""
        print("Generating initial requirements from baseline:", baseline_summary[:200])

        prompt = f"""Based on this system description: "{baseline_summary}"

Generate exactly 20 software requirements appropriate for this system: 10 functional and 10 non-functional (include performance, security, reliability, and usability where relevant).

Output format — nothing else, no numbering, no markdown, no category headers:
Each line is one requirement, starting with REQ: then The system shall ...
Example line: REQ: The system shall authenticate users before granting access to protected data.

Each requirement MUST be on its own line (one REQ: per line)."""

        try:
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=3500,
            )

            content = response.choices[0].message.content.strip()
            content = re.sub(r"(?<![\r\n])\s*(?=REQ:)", "\n", content, flags=re.IGNORECASE)
            reqs = []

            lines = [line.replace("**", "").strip() for line in content.split("\n") if line.strip()]
            for line in lines:
                if line.upper().startswith("REQ:"):
                    parts = re.split(r"REQ:", line, flags=re.IGNORECASE)
                    if len(parts) > 1:
                        text = " ".join(parts[1].split())
                        if text:
                            reqs.append(text)

            if not reqs:
                print(f"⚠️ Parsing failed. Raw LLM Content:\n{content}")
                raise ValueError("Failed to parse LLM response")

            return list(DEFAULT_BASELINE_ASPECTS), reqs[:20]

        except Exception as e:
            print(f"❌ Error generating aspects: {str(e)}")
            return list(DEFAULT_BASELINE_ASPECTS), [
                "The system shall authenticate users before granting access to protected functionalities.",
                "The system shall provide a user interface to interact with core features.",
                "The system shall store all user data securely in a centralized database.",
                "The system shall protect against unauthorized data access.",
                "The system shall remain responsive during concurrent user access.",
            ]

    async def collect_baseline(self, conv_id, user_input):
        """Collect and process baseline system summary - with LLM validation and automatic initial requirements"""
        self.load_session(conv_id)

        if conv_id not in self.sessions:
            self.sessions[conv_id] = {
                'baseline': None,
                'requirements_list': [],
                'baseline_collected': False,
                'aspects_covered': [],
                'baseline_aspects': [],
                'memory': ConversationBufferWindowMemory(k=10, return_messages=True)
            }

        if self.sessions[conv_id]['memory'] is None:
            self.sessions[conv_id]['memory'] = ConversationBufferWindowMemory(k=10, return_messages=True)

        # Use LLM to validate if this is realistic software
        validation_result = self._validate_system_description(user_input)

        if not validation_result["is_valid"]:
            return {
                "response": validation_result["message"],
                "aspects": [],
                "requirements": list(
                    self.sessions.get(conv_id, {}).get("requirements_list") or []
                ),
            }

        # Generate both aspects and initial domain-specific requirements
        aspects, initial_reqs = self.generate_aspects_and_initial_requirements(user_input.strip())

        self.sessions[conv_id]['baseline'] = user_input.strip()
        self.sessions[conv_id]['baseline_aspects'] = aspects
        self.sessions[conv_id]['baseline_collected'] = True
        
        # Automatically store the generated initial requirements
        for req in initial_reqs:
            self.store_requirement(conv_id, req)
            
        self.save_session(conv_id)

        aspects_text = "\n".join([f"  • {aspect}" for aspect in aspects])
        reqs_text = "\n".join([f"  • {req}" for req in initial_reqs])

        response = f"""Thank you! I've recorded your system description:

"{user_input}"

We'll align elicitation with this standard coverage checklist:
{aspects_text}

I have automatically generated and saved these initial foundational requirements for your project:
{reqs_text}

Now, let's start collecting detailed requirements. Please describe specific features and functionalities you need.

Commands you can use anytime:
- "show requirements" - Display collected requirements
- "end" or "finish" - Complete the elicitation session"""

        return {
            "response": response,
            "aspects": self.sessions[conv_id]["baseline_aspects"],
            "requirements": list(self.sessions[conv_id]["requirements_list"]),
        }

    def _validate_requirement_input(self, user_input, memory_history):
        # Get the last thing the bot asked
        last_question = ""
        if memory_history and len(memory_history) > 0:
            # Look for the last AI message
            for msg in reversed(memory_history):
                if msg.type == 'ai':
                    last_question = msg.content
                break

        validation_prompt = f"""Validate if this requirement is acceptable for a software system.
        System: {self.system_baseline}
        Recent Bot Question: "{last_question}"
        User input: "{user_input}"

ONLY REJECT if input clearly requires IMPOSSIBLE technology:
- Time travel, teleportation, mind reading, magic, breaking physics

ACCEPT everything else:
- Realistic features (even if ambitious)
- Questions about the system
- Feature descriptions
- Technical requirements

Be LENIENT. Most inputs should be ACCEPTED.

Response (one word):
- ACCEPT (if realistic or unclear)
- REJECT (if clearly requires impossible technology)

Your answer:"""

        try:
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": validation_prompt}],
                temperature=0.1,
                max_tokens=30
            )

            result = response.choices[0].message.content.strip().upper()

            if "ACCEPT" in result or "VALID" in result:
                return {'is_valid': True, 'message': None}
            elif "REJECT" in result:
                return {
                    'is_valid': False,
                    'message': f"❌ This requirement involves impossible technology.\n\nPlease describe realistic software features for your system: {self.system_baseline}"
                }
            else:
                # Default to accept if unclear
                return {'is_valid': True, 'message': None}
        except:
            # If API fails, allow to be safe (don't block valid requirements)
            return {'is_valid': True, 'message': None}

    def _validate_system_description(self, user_input):
        """Comprehensive LLM-based validation of system description"""
        validation_prompt = f"""You are a STRICT validator. Analyze if this system requires IMPOSSIBLE technology.

Input: "{user_input}"

STEP 1 - Check for IMPOSSIBLE TECHNOLOGY:
REJECT if the system requires ANY of these:
- TIME TRAVEL (traveling to past/future, changing history, viewing past events live)
- TELEPORTATION (instantly moving objects/people across physical space)
- MIND READING / MIND CONTROL / TELEPATHY (reading thoughts, controlling minds, brain-to-brain communication without physical devices)
- PREDICTING FUTURE with certainty (not AI predictions, but knowing actual future events)
- MAGIC, supernatural powers, psychic abilities
- IMMORTALITY, resurrection, stopping biological aging
- BREAKING LAWS OF PHYSICS (FTL travel, perpetual motion, creating energy from nothing)

STEP 2 - Check if it's about SOFTWARE:
REJECT if: Not about software at all (personal stories, cooking, pure hardware with no software component)
ACCEPT if: Any software system, app, platform, or digital service

CRITICAL EXAMPLES:
- "Mind control system" = REJECT_IMPOSSIBLE (mind control is impossible)
- "Brain control interface" = REJECT_IMPOSSIBLE (controlling brain/mind is impossible)
- "Read thoughts app" = REJECT_IMPOSSIBLE (reading thoughts is impossible)
- "Time travel system" = REJECT_IMPOSSIBLE (time travel is impossible)
- "Teleport service" = REJECT_IMPOSSIBLE (teleportation is impossible)
- "Hospital management" = ACCEPT (realistic software)
- "Staff scheduling" = ACCEPT (realistic software)
- "AI prediction app" = ACCEPT (AI predictions are possible)

BE STRICT about impossible technology. If core functionality is impossible, REJECT.

Response (choose ONE, single word):
- ACCEPT
- REJECT_IMPOSSIBLE
- REJECT_NOT_SOFTWARE

Your answer:"""

        try:
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": validation_prompt}],
                temperature=0.05,  # Very low temperature for strict, deterministic validation
                max_tokens=20
            )

            result = response.choices[0].message.content.strip().upper()

            # Check for rejection first (more important to catch impossible systems)
            if "REJECT_IMPOSSIBLE" in result or ("REJECT" in result and "IMPOSSIBLE" in result):
                return {
                    'is_valid': False,
                    'message': f"""❌ REJECTED: This system requires IMPOSSIBLE technology.

Your input: "{user_input}"

I can ONLY help with REALISTIC software that can be built with current technology.

❌ I CANNOT help with systems requiring:
- Time travel, teleportation, mind reading, or mind control
- Magic, supernatural powers, psychic abilities
- Predicting actual future events with certainty
- Immortality, resurrection, breaking laws of physics

✅ I CAN help with realistic software like:
- E-commerce platforms, social media apps
- Mobile apps for productivity or communication
- Business management systems (CRM, ERP, HMS, inventory)
- AI/ML systems (recommendations, predictions, analysis)
- Healthcare software, scheduling systems
- Booking, scheduling, or reservation systems
- Payment processing, authentication systems

Please describe a REALISTIC software system."""
                }

            elif "REJECT_NOT_SOFTWARE" in result or ("REJECT" in result and "SOFTWARE" in result):
                return {
                    'is_valid': False,
                    'message': f"""I am a requirements gathering expert for SOFTWARE systems only.

Your input: "{user_input}"

✅ Please describe a SOFTWARE SYSTEM such as:
- Web applications (e-commerce, social media, booking systems)
- Mobile applications (productivity, communication, utilities)
- Business systems (CRM, ERP, HMS, inventory management)
- Database systems or APIs
- Management platforms

Example: "An e-commerce platform where users can browse products, add items to cart, and checkout securely."

What software system would you like to gather requirements for?"""
                }

            elif "ACCEPT" in result:
                return {'is_valid': True, 'message': None}
            else:
                # If unclear response, be lenient and accept
                return {'is_valid': True, 'message': None}

        except Exception as e:
            # If API fails, ACCEPT to be lenient (don't block valid requirements)
            return {'is_valid': True, 'message': None}

    def extract_and_validate_requirements(self, conv_id, user_input):
        """Extract requirements from user input and save them exactly word-for-word"""
        if conv_id not in self.sessions or not self.sessions[conv_id]['baseline_collected']:
            return "Please provide a baseline system description first."

        if self.sessions[conv_id]['memory'] is None:
            self.sessions[conv_id]['memory'] = ConversationBufferWindowMemory(k=10, return_messages=True)

        memory = self.sessions[conv_id]['memory']
        conversation_history = memory.load_memory_variables({})["history"]

        messages = [
            {"role": "system", "content": self.system_prompt + f"""

SYSTEM CONTEXT:
- System baseline: {self.sessions[conv_id]['baseline']}
- Aspects to cover: {', '.join(self.sessions[conv_id]['baseline_aspects'])}
- Aspects already covered: {', '.join(self.sessions[conv_id]['aspects_covered']) if self.sessions[conv_id]['aspects_covered'] else 'None yet'}

REMEMBER: Use the conversation history to maintain context and avoid repeating questions."""}
        ]

        # Add conversation history to maintain context
        for msg in conversation_history:
            if hasattr(msg, 'type') and hasattr(msg, 'content'):
                if msg.type == 'human':
                    messages.append({"role": "user", "content": msg.content})
                elif msg.type == 'ai':
                    messages.append({"role": "assistant", "content": msg.content})

        # Add current user input
        messages.append({"role": "user", "content": user_input})

        try:
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                temperature=0.2,
                max_tokens=400
            )

            response_text = response.choices[0].message.content

            # Parse and store requirements from response exactly word for word
            extracted_reqs = []
            for line in response_text.split('\n'):
                line = line.strip()
                # Clean up markdown list formatting, but keep the core requirement intact
                clean_line = re.sub(r'^(\d+\.|[-*])\s*', '', line).strip()
                clean_line = clean_line.replace('**', '') 
                
                # Check for the explicit prefix we instructed the LLM to use
                if 'REQUIREMENT:' in clean_line:
                    req_text = clean_line.split('REQUIREMENT:')[1].strip()
                    if req_text:
                        extracted_reqs.append(req_text)
                # Fallback backup rule to catch other plain requirement statements
                elif clean_line.lower().startswith('the system shall') or clean_line.lower().startswith('the user shall'):
                    extracted_reqs.append(clean_line)

            for req in extracted_reqs:
                self.store_requirement(conv_id, req.strip())

            # Save to memory
            memory.save_context(
                {"input": user_input},
                {"output": response_text}
            )

            return response_text

        except Exception as e:
            return "I apologize, I'm having trouble processing that. Could you rephrase your requirement?"

    def store_requirement(self, conv_id, requirement_text):
        """Store a validated requirement"""
        # Clean up the requirement
        req = requirement_text.strip()

        # Check for duplicates
        if any(self._is_similar(req, existing) for existing in self.sessions[conv_id]['requirements_list']):
            return False, "This requirement seems similar to one already collected."

        self.sessions[conv_id]['requirements_list'].append(req)

        # Try to determine which aspect this covers
        self._update_covered_aspects(conv_id, req)

        self.save_session(conv_id)
        return True, f"Requirement added. Total: {len(self.sessions[conv_id]['requirements_list'])}"

    def delete_requirement(self, conv_id, index):
        """Delete a requirement by its list index and update session state."""
        if conv_id not in self.sessions:
            return False, "Session not found."
            
        req_list = self.sessions[conv_id].get('requirements_list', [])
        
        if not isinstance(index, int) or index < 0 or index >= len(req_list):
            return False, f"Invalid requirement index: {index}."
            
        # Remove the requirement
        deleted_req = req_list.pop(index)
        
        # Recalculate which aspects are still covered
        self._recalculate_aspects(conv_id)
        
        # Save the updated state to the JSON file
        self.save_session(conv_id)
        
        return True, f"Requirement deleted successfully."

    def edit_requirement(self, conv_id, index, new_text):
        """Edit an existing requirement by its list index and update session state."""
        if conv_id not in self.sessions:
            return False, "Session not found."
            
        req_list = self.sessions[conv_id].get('requirements_list', [])
        
        if not isinstance(index, int) or index < 0 or index >= len(req_list):
            return False, f"Invalid requirement index: {index}."
            
        # Update the requirement
        req_list[index] = new_text.strip()
        
        # Recalculate which aspects are covered (in case the edit changed the core topic)
        self._recalculate_aspects(conv_id)
        
        # Save the updated state to the JSON file
        self.save_session(conv_id)
        
        return True, "Requirement updated successfully."

    def _recalculate_aspects(self, conv_id):
        """Re-evaluate all current requirements to determine which aspects are covered."""
        # Reset the covered aspects list
        self.sessions[conv_id]['aspects_covered'] = []
        
        # Re-run the aspect detection for all remaining requirements
        req_list = self.sessions[conv_id].get('requirements_list', [])
        for req in req_list:
            self._update_covered_aspects(conv_id, req)

    def _is_similar(self, req1, req2):
        """Check if two requirements are similar (basic similarity check)"""
        # Simple word overlap check
        words1 = set(req1.lower().split())
        words2 = set(req2.lower().split())
        overlap = len(words1.intersection(words2)) / max(len(words1), len(words2))
        return overlap > 0.7

    def _update_covered_aspects(self, conv_id, requirement):
        """Update aspects covered based on requirement content"""
        req_lower = requirement.lower()

        for aspect in self.sessions[conv_id]['baseline_aspects']:
            aspect_words = aspect.lower().split()
            if any(word in req_lower for word in aspect_words if len(word) > 3):
                if aspect not in self.sessions[conv_id]['aspects_covered']:
                    self.sessions[conv_id]['aspects_covered'].append(aspect)


    def display_requirements(self, conv_id):
        """Display all collected requirements"""
        if conv_id not in self.sessions or not self.sessions[conv_id]['requirements_list']:
            return "No requirements collected yet."

        output = "Requirements collected so far:\n"
        output += "=" * 50 + "\n"

        for i, req in enumerate(self.sessions[conv_id]['requirements_list'], 1):
            output += f"{i}. {req}\n"

        output += "\n" + "=" * 50
        output += f"\nTotal: {len(self.sessions[conv_id]['requirements_list'])} requirements"

        # Show coverage
        uncovered = set(self.sessions[conv_id]['baseline_aspects']) - set(self.sessions[conv_id]['aspects_covered'])

        if uncovered:
            output += f"\n\nAspects not yet covered: {', '.join(uncovered)}"

        return output

    async def end_elicitation(self, conv_id):
        """Final requirements display and coverage check"""
        from orchestrator.shared_state import get_shared_state

        if conv_id not in self.sessions:
            return {
                "project_title": "Project",
                "project_description": "",
                "requirements_list": [],
                "final_output": "No session found.",
            }

        session = self.sessions[conv_id]

        shared = get_shared_state()
        conv = shared.get_conversation(conv_id)
        project_title = (conv.get("metadata") or {}).get("title") or "Project"
        project_description = (
            shared.get_project_description(conv_id)
            or session.get("baseline")
            or ""
        )

        # Ensure lists are not None
        baseline_aspects = session.get('baseline_aspects', []) or []
        aspects_covered = session.get('aspects_covered', []) or []
        requirements_list = session.get('requirements_list', []) or []
        baseline = session.get('baseline', '')

        # Check coverage
        uncovered = set(baseline_aspects) - set(aspects_covered)

        output = "Final Requirement List\n"

        if not requirements_list:
            output += "No requirements were collected.\n"
        else:
            for i, req in enumerate(requirements_list, 1):
                output += f"{i}. {req}\n"

        

        if uncovered:
            output += f"\n Note: The following aspects were not covered:\n"
            for aspect in uncovered:
                output += f"   • {aspect}\n"

        return {
            "project_title": project_title,
            "project_description": project_description or baseline,
            "requirements_list": requirements_list,
            "final_output": output,
        }

    def check_command(self, user_input):
        """Check if user input is an exact command"""
        input_lower = user_input.lower().strip()

        # Exact match for display commands
        if input_lower in ['show requirements', 'list requirements', 'display requirements', 'what do we have']:
            return 'display'

        # Exact match for end commands
        if input_lower in ['end', 'finish', 'done', 'complete', 'confirm end']:
            return 'end'

        return None


    async def chat(self, conv_id, user_input, form_info):

        self.project_title = form_info['project_title']
        self.project_description = form_info['project_description']
        """Main chat method"""
        if not user_input.strip():
            return {'response': "Please provide input.", 'requirements': []}

        user_input = user_input.strip()

        # Check for commands first
        command = self.check_command(user_input)

        if command == 'display':
            reqs = self.sessions.get(conv_id, {}).get('requirements_list', [])
            return {'response': self.display_requirements(conv_id), 'requirements': reqs}

        elif command == 'end':
            # Call the actual end_elicitation method instead of just displaying!
            end_result = await self.end_elicitation(conv_id)
            return {
                'response': end_result['final_output'],
                'requirements': end_result['requirements_list']
            }

        self.load_session(conv_id)

        # If baseline not collected, collect it first
        if conv_id not in self.sessions or not self.sessions[conv_id].get('baseline_collected', False):
            return await self.collect_baseline(conv_id, user_input)

        # Ensure we set the system baseline so the validation prompt knows what system we're talking about
        self.system_baseline = self.sessions[conv_id].get('baseline')

        # Validate using LLM for requirements input
        memory_history = self.sessions[conv_id]['memory'].load_memory_variables({})["history"]
        validation_result = self._validate_requirement_input(user_input, memory_history)
        if not validation_result['is_valid']:
            return {
                'response': validation_result['message'],
                'requirements': self.sessions[conv_id].get('requirements_list', [])
            }

        # Process requirement
        response_text = self.extract_and_validate_requirements(conv_id, user_input)

        return {
            'response': response_text,
            'requirements': self.sessions[conv_id].get('requirements_list', [])
        }

    async def chat_with_confirmation(self, conv_id, user_input):
        """Enhanced chat with requirement confirmation flow (primarily for CLI usage)"""
        result = await self.chat(conv_id, user_input)
        response = result['response']

        # Check if response contains a "shall" statement AND is asking a question - likely a requirement to confirm
        if "shall" in response and "?" in response:
            lines = response.split('\n')
            for line in lines:
                # Adapted to also catch lines prefixed with REQUIREMENT:
                clean_line = line.replace('REQUIREMENT:', '').strip()
                if "shall" in clean_line.lower() and not clean_line.startswith('-'):
                    self.awaiting_confirmation = clean_line
                    break

        # Check if user is confirming
        if getattr(self, 'awaiting_confirmation', None) and any(word in user_input.lower() for word in ['yes', 'correct', 'right', 'confirm', 'yep', 'yeah']):
            success, message = self.store_requirement(conv_id, self.awaiting_confirmation)
            self.awaiting_confirmation = None
            if success:
                return f"✓ {message}\n\nPlease continue with more requirements, or type 'show requirements' to see what we have."
            else:
                return message

        return response

def main():
    bot = ImprovedRequirementsElicitation()
    cli_session_id = "cli-session-1"

    print("=" * 70)
    print("REQUIREMENTS ELICITATION SYSTEM")
    print("=" * 70)
    print("Using EARS (Easy Approach to Requirements Syntax) methodology")
    print("Powered by: llama-3.3-70b-versatile")
    print("=" * 70)

    # MINIMAL CHANGE: Added cli_session_id to prevent class methods from throwing TypeError
    if bot.load_session(cli_session_id):
        print("\n✓ Previous session loaded!")
        print(f"System: {bot.sessions[cli_session_id].get('baseline')}")
        print(f"Requirements collected: {len(bot.sessions[cli_session_id].get('requirements_list', []))}")
        resume = input("\nContinue previous session? (yes/no): ").strip().lower()
        if resume != 'yes':
            bot = ImprovedRequirementsElicitation()  # Start fresh
            print("\nStarting new session...")

    is_baseline_collected = bot.sessions.get(cli_session_id, {}).get('baseline_collected', False)

    if not is_baseline_collected:
        print("\n📋 STEP 1: System Baseline")
        print("-" * 70)
        print("First, please provide a brief summary of your system (2-3 sentences).")
        print("This helps ensure we collect complete requirements.\n")
        print("Example: 'An e-commerce platform where users can browse products,")
        print("        add items to cart, and checkout securely.'\n")

    print("\nCommands:")
    print("  • 'show requirements' - View collected requirements")
    print("  • 'end' or 'finish'  - Complete elicitation session")
    print("  • 'quit'             - Exit without saving")
    print("=" * 70)

    while True:
        try:
            is_baseline_collected = bot.sessions.get(cli_session_id, {}).get('baseline_collected', False)
            if not is_baseline_collected:
                user_input = input("\n📋 System Summary: ").strip()
            else:
                user_input = input("\n💬 You: ").strip()

            if user_input.lower() in ['quit', 'exit']:
                confirm = input("\nAre you sure you want to exit? Progress is saved. (yes/no): ")
                if confirm.lower() == 'yes':
                    print("\n👋 Goodbye! Your session has been saved.")
                    break
                else:
                    continue

            if not user_input:
                continue

            print("\n🤖 Assistant: ", end="")
            import asyncio
            response = asyncio.run(bot.chat_with_confirmation(cli_session_id, user_input))
            print(response)

        except KeyboardInterrupt:
            print("\n\n⚠️  Interrupted. Your progress has been saved.")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("Please try again.")

if __name__ == "__main__":
    main()