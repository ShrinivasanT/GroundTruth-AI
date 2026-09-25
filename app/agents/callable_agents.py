"""Specialty Agents — Callable LangGraph nodes powered by gpt-5-mini.

This module houses the factories for the three user-triggered specialty agents:
- Buddy Agent (@buddy): Code compiler with Docker verification and self-correction.
- Review Agent (@review): Critical scientific peer-evaluator.
- Writer Agent (@writer): Documentation compiler and programmatic Word exporter.
"""

from __future__ import annotations

import logging
import os
import re
import time
from typing import TYPE_CHECKING

from langchain_openai import ChatOpenAI

from app.agents.state import AgentState
from app.utils.sandbox import run_code_in_sandbox
from app.utils.docx_generator import generate_docx_from_markdown

if TYPE_CHECKING:
    from app.core.config import Settings
    from app.retrieval.service import HybridRetriever

logger = logging.getLogger(__name__)


def make_buddy_node(settings: Settings, retriever: HybridRetriever):
    """Return an async LangGraph node for the Buddy (@buddy) Agent.

    Generates boilerplate code, executes it inside an isolated Docker slim container,
    self-corrects via LLM loop if errors arise, and appends testing diagnostics.
    """
    llm = ChatOpenAI(
        model=settings.openai_chat_model,
        api_key=settings.openai_api_key,
        temperature=0.2,
    )

    async def buddy_agent(state: AgentState) -> dict:
        query = state["query"]
        clean_query = re.sub(r"@buddy\b", "", query, flags=re.IGNORECASE).strip()

        top_k = state.get("top_k", 8)
        session_id = state.get("session_id")
        category = state.get("category")

        # Dynamically enrich agent context with targeted retrieval
        hits = await retriever.retrieve(
            clean_query,
            top_k,
            session_id=session_id,
            category=category,
        )

        evidence_block = ""
        if hits:
            evidence_lines = []
            for hit in hits:
                page_info = f", Page {hit.page}" if hit.page else ""
                evidence_lines.append(
                    f"[{hit.citation_label}] ({hit.title}{page_info}):\n{hit.content}"
                )
            evidence_block = "\n\n".join(evidence_lines)

        system_prompt = (
            "You are a programming companion and technical implementation expert. Your goal is to draft "
            "production-ready boilerplate code, architectures, and implementations based on the techniques, "
            "equations, or algorithms outlined in the retrieved academic paper segments.\n\n"
            "Rules:\n"
            "1. Provide complete, well-commented, and robust code snippets (preferably in Python).\n"
            "2. Ground your implementation directly by referencing paper methods and citation labels (e.g. [C1]).\n"
            "3. Structure your response clearly using Markdown headers, detailing code parameters, library requirements, and execution examples.\n"
            "4. If you write executable code, place the primary executable block inside a standard ```python block."
        )

        user_content = (
            f"User query: {clean_query}\n\n"
            f"Evidence:\n{evidence_block if evidence_block else 'No indexed paper segments available for this session.'}"
        )

        # Primary generation
        try:
            response = await llm.ainvoke(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ]
            )
            answer = response.content.strip()
        except Exception as e:
            logger.exception("BuddyAgent: LLM call failed")
            return {"final_answer": f"An error occurred in Buddy Agent: {e}", "retrieval_hits": hits}

        # Subprocess Docker testing and Self-Correction Loop (Up to 2 cycles)
        max_attempts = 2
        for attempt in range(1, max_attempts + 1):
            # Extract python code block
            code_match = re.search(r"```python\n(.*?)```", answer, re.DOTALL)
            if not code_match:
                logger.info("BuddyAgent: no executable code blocks found to test.")
                break

            code_to_test = code_match.group(1)
            sandbox_result = await run_code_in_sandbox(code_to_test)

            if sandbox_result["success"]:
                logger.info("BuddyAgent: Docker sandbox test succeeded on attempt %d", attempt)
                # Append success log to output
                sandbox_log = (
                    "\n\n---\n### 🔬 Sandbox Verification Log\n"
                    "```text\n"
                    "Status: SUCCESS\n"
                    f"Stdout:\n{sandbox_result['stdout'] or '(No output)'}\n"
                    "```"
                )
                answer += sandbox_log
                break
            else:
                logger.warning("BuddyAgent: Docker sandbox test failed on attempt %d", attempt)
                if attempt == max_attempts:
                    # Final attempt failed — append failure log to output
                    sandbox_log = (
                        "\n\n---\n### 🔬 Sandbox Verification Log\n"
                        "```text\n"
                        f"Status: FAILED (Exit Code {sandbox_result['exit_code']})\n"
                        f"Stderr:\n{sandbox_result['stderr']}\n"
                        f"Stdout:\n{sandbox_result['stdout'] or '(No output)'}\n"
                        "```\n"
                        "> [!WARNING]\n"
                        "> The generated code could not execute successfully in the Docker sandbox. See logs above."
                    )
                    answer += sandbox_log
                    break

                # Self-correction LLM prompt
                correction_prompt = (
                    f"The code you generated on attempt {attempt} failed to execute in the secure isolated Docker sandbox.\n\n"
                    f"### Code Attempt:\n```python\n{code_to_test}\n```\n\n"
                    f"### Execution Error:\n{sandbox_result['stderr']}\n\n"
                    f"### Execution Output:\n{sandbox_result['stdout']}\n\n"
                    "Please locate the bug, correct it, and return the entire updated answer. Ensure all complete "
                    "code blocks remain enclosed in standard ```python tags."
                )
                try:
                    response = await llm.ainvoke(
                        [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_content},
                            {"role": "assistant", "content": answer},
                            {"role": "user", "content": correction_prompt},
                        ]
                    )
                    answer = response.content.strip()
                except Exception as e:
                    logger.exception("BuddyAgent: Self-correction LLM call failed")
                    break

        return {
            "final_answer": answer,
            "retrieval_hits": hits,
            "relevance_scores": [h.score for h in hits],
        }

    return buddy_agent


def make_review_node(settings: Settings, retriever: HybridRetriever):
    """Return an async LangGraph node for the Review (@review) Agent.

    Generates critical, structured scientific reviews and peer critiques.
    """
    llm = ChatOpenAI(
        model=settings.openai_chat_model,
        api_key=settings.openai_api_key,
        temperature=0.3,
    )

    async def review_agent(state: AgentState) -> dict:
        query = state["query"]
        clean_query = re.sub(r"@review\b", "", query, flags=re.IGNORECASE).strip()

        top_k = state.get("top_k", 8)
        session_id = state.get("session_id")
        category = state.get("category")
        session_topic = state.get("session_topic")

        # Retrieve relevant segments. Default to topic/general review if clean_query is empty.
        search_term = clean_query if clean_query else (session_topic or "scientific overview")
        hits = await retriever.retrieve(
            search_term,
            top_k,
            session_id=session_id,
            category=category,
        )

        evidence_block = ""
        if hits:
            evidence_lines = []
            for hit in hits:
                page_info = f", Page {hit.page}" if hit.page else ""
                evidence_lines.append(
                    f"[{hit.citation_label}] ({hit.title}{page_info}):\n{hit.content}"
                )
            evidence_block = "\n\n".join(evidence_lines)

        system_prompt = (
            "You are an expert scientific reviewer and peer evaluator. Your task is to perform a rigorous "
            "scientific review and critical critique of the theories, methodologies, experiments, and conclusions "
            "presented in the active papers.\n\n"
            "Rules:\n"
            "1. Structure your output as a formal academic review using professional Markdown headers "
            "(e.g., Executive Summary, Methodological Analysis, Strengths, Weaknesses & Limitations, Verdict & Recommendations).\n"
            "2. Ground every criticism, positive or negative, in specific paper segments, referencing citation labels (e.g. [C1]).\n"
            "3. Maintain a neutral, professional, and intellectually rigorous academic tone.\n"
            "4. Synthesize context from the initial session learning topic to ensure the critique aligns with the session objective."
        )

        topic_str = f"Active Session Topic: {session_topic}\n" if session_topic else ""
        user_content = (
            f"{topic_str}User review query: {clean_query if clean_query else 'Critique the active paper corpus.'}\n\n"
            f"Evidence:\n{evidence_block if evidence_block else 'No indexed paper segments available for this session.'}"
        )

        try:
            response = await llm.ainvoke(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ]
            )
            answer = response.content.strip()
        except Exception as e:
            logger.exception("ReviewAgent: LLM call failed")
            answer = f"An error occurred in Review Agent while generating the scientific evaluation: {e}"

        return {
            "final_answer": answer,
            "retrieval_hits": hits,
            "relevance_scores": [h.score for h in hits],
        }

    return review_agent


def make_writer_node(settings: Settings, retriever: HybridRetriever):
    """Return an async LangGraph node for the Writer (@writer) Agent.

    Generates formal technical reports and programmatically compiles them
    into downloadable Word (.docx) files.
    """
    llm = ChatOpenAI(
        model=settings.openai_chat_model,
        api_key=settings.openai_api_key,
        temperature=0.3,
    )

    async def writer_agent(state: AgentState) -> dict:
        query = state["query"]
        clean_query = re.sub(r"@writer\b", "", query, flags=re.IGNORECASE).strip()

        top_k = state.get("top_k", 8)
        session_id = state.get("session_id")
        category = state.get("category")
        session_topic = state.get("session_topic")

        search_term = clean_query if clean_query else (session_topic or "technical summary")
        hits = await retriever.retrieve(
            search_term,
            top_k,
            session_id=session_id,
            category=category,
        )

        evidence_block = ""
        if hits:
            evidence_lines = []
            for hit in hits:
                page_info = f", Page {hit.page}" if hit.page else ""
                evidence_lines.append(
                    f"[{hit.citation_label}] ({hit.title}{page_info}):\n{hit.content}"
                )
            evidence_block = "\n\n".join(evidence_lines)

        system_prompt = (
            "You are a professional technical writer and research document compiler. Your task is to synthesize findings, "
            "architectural details, and algorithms from the active papers into a structured, comprehensive, and clean "
            "Markdown technical report.\n\n"
            "Rules:\n"
            "1. Compile a high-quality technical report using hierarchical Markdown headers, structured bullet points, and data tables.\n"
            "2. Synthesize facts cohesively across multiple paper sources, avoiding speculation.\n"
            "3. Ensure all claims are properly cited using inline citation labels (e.g. [C1]).\n"
            "4. Organize the document into logical sections (e.g., Executive Overview, System Architecture, Core Contributions, Specifications, References)."
        )

        topic_str = f"Active Session Topic: {session_topic}\n" if session_topic else ""
        user_content = (
            f"{topic_str}User documentation query: {clean_query if clean_query else 'Draft a technical summary of findings.'}\n\n"
            f"Evidence:\n{evidence_block if evidence_block else 'No indexed paper segments available for this session.'}"
        )

        try:
            response = await llm.ainvoke(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ]
            )
            answer = response.content.strip()

            # Compile to .docx programmatically
            filename = f"doc_{session_id or 'anon'}_{int(time.time())}.docx"
            output_dir = os.path.join("storage", "temp")
            output_path = os.path.join(output_dir, filename)

            # Convert markdown layout to word
            generate_docx_from_markdown(answer, output_path)

            # Append document save notice
            doc_notice = (
                "\n\n---\n### 📄 Programmatic Word Export\n"
                f"The structured documentation has been programmatically compiled into a Word Document.\n"
                f"- **Save Path**: `{output_path}`"
            )
            answer += doc_notice

        except Exception as e:
            logger.exception("WriterAgent: compilation failed")
            answer = f"An error occurred in Writer Agent: {e}"

        return {
            "final_answer": answer,
            "retrieval_hits": hits,
            "relevance_scores": [h.score for h in hits],
        }

    return writer_agent
