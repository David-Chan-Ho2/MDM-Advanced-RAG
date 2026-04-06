from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed

from loguru import logger

from agents.specialized import (
    DimensionsAgent,
    ElectricalAgent,
    IdentifiersAgent,
    MaterialsAgent,
    PerformanceAgent,
)
from agents.validator import ExtractionValidator


class ExtractionOrchestrator:
    """Routes a document through all specialized agents and merges the result."""

    def __init__(
        self,
        agents: list | None = None,
        validator: ExtractionValidator | None = None,
    ):
        self._agents = agents or [
            IdentifiersAgent(),
            DimensionsAgent(),
            ElectricalAgent(),
            MaterialsAgent(),
            PerformanceAgent(),
        ]
        self._validator = validator or ExtractionValidator()

    def extract_document(
        self,
        document_id: str,
        document_filename: str,
        filters: dict | None = None,
    ):
        agent_results = []

        with ThreadPoolExecutor(max_workers=len(self._agents)) as executor:
            futures = {
                executor.submit(
                    agent.extract,
                    document_id=document_id,
                    document_filename=document_filename,
                    filters=filters,
                ): agent
                for agent in self._agents
            }

            for future in as_completed(futures):
                agent = futures[future]
                try:
                    agent_results.append(future.result())
                except Exception as exc:
                    logger.exception(f"{agent.name} failed for {document_id}: {exc}")
                    agent_results.append(agent.empty_result(notes=str(exc)))

        agent_results.sort(key=lambda result: result.agent_name)
        return self._validator.merge(document_id, document_filename, agent_results)
