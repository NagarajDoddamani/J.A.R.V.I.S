from __future__ import annotations

from datetime import datetime, timezone

from backend.agent.domain.model import (
    Agent,
    AgentCreated,
    AgentExecution,
    AgentExecutionCompleted,
    AgentExecutionFailed,
    AgentExecutionId,
    AgentExecutionStarted,
    AgentGoal,
    AgentId,
    AgentInstruction,
    AgentName,
    AgentResult,
    AgentStatus,
    AgentTask,
    AgentTaskCancelled,
    AgentTaskCompleted,
    AgentTaskCreated,
    AgentTaskFailed,
    AgentTaskId,
    AgentTaskStarted,
    AgentType,
    FailureReason,
)
from backend.agent.domain.rules import (
    assert_agent_goal_required,
    assert_agent_instruction_required,
    assert_agent_name_required,
    assert_agent_type_valid,
    assert_failure_reason_required,
    assert_agent_result_required,
)


class AgentFactory:
    """Factory for creating validated agent domain aggregates."""

    @staticmethod
    def create_agent(
        *,
        name: str,
        agent_type: str | AgentType = AgentType.COORDINATOR,
    ) -> tuple[Agent, AgentCreated]:
        assert_agent_name_required(name)
        if isinstance(agent_type, str):
            assert_agent_type_valid(agent_type)
            agent_type = AgentType(agent_type)

        name_vo = AgentName(value=name)
        now = datetime.now(tz=timezone.utc)

        agent = Agent(
            agent_id=AgentId(),
            agent_type=agent_type,
            name=name_vo,
            status=AgentStatus.IDLE,
            created_at=now,
        )

        event = AgentCreated(
            agent_id=agent.agent_id,
            agent_type=agent_type.value,
            name=name,
            occurred_at=now,
        )

        return agent, event

    @staticmethod
    def activate_agent(agent: Agent) -> None:
        agent.activate()

    @staticmethod
    def pause_agent(agent: Agent) -> None:
        agent.pause()

    @staticmethod
    def disable_agent(agent: Agent) -> None:
        agent.disable()

    @staticmethod
    def create_task(
        *,
        agent: Agent,
        goal: str,
        instruction: str,
    ) -> tuple[AgentTask, AgentTaskCreated]:
        assert_agent_goal_required(goal)
        assert_agent_instruction_required(instruction)

        goal_vo = AgentGoal(value=goal)
        instruction_vo = AgentInstruction(value=instruction)

        task = AgentTask(
            task_id=AgentTaskId(),
            goal=goal_vo,
            instruction=instruction_vo,
        )

        agent.add_task(task)
        event = agent.events[-1]

        return task, event

    @staticmethod
    def start_task(
        *,
        agent: Agent,
        task_id: AgentTaskId,
    ) -> AgentTaskStarted:
        agent.start_task(task_id)
        return agent.events[-1]

    @staticmethod
    def complete_task(
        *,
        agent: Agent,
        task_id: AgentTaskId,
        result: str,
    ) -> AgentTaskCompleted:
        result_vo = AgentResult(value=result)
        agent.complete_task(task_id, result_vo)
        return agent.events[-1]

    @staticmethod
    def fail_task(
        *,
        agent: Agent,
        task_id: AgentTaskId,
        reason: str,
    ) -> AgentTaskFailed:
        reason_vo = FailureReason(value=reason)
        agent.fail_task(task_id, reason_vo)
        return agent.events[-1]

    @staticmethod
    def cancel_task(
        *,
        agent: Agent,
        task_id: AgentTaskId,
    ) -> AgentTaskCancelled:
        agent.cancel_task(task_id)
        return agent.events[-1]

    @staticmethod
    def start_execution(
        *,
        agent: Agent,
        task_id: AgentTaskId,
    ) -> tuple[AgentExecution, AgentExecutionStarted]:
        execution = agent.start_execution(task_id)
        event = agent.events[-1]
        return execution, event

    @staticmethod
    def complete_execution(
        *,
        agent: Agent,
        execution_id: AgentExecutionId,
        result: str,
    ) -> AgentExecutionCompleted:
        result_vo = AgentResult(value=result)
        agent.complete_execution(execution_id, result_vo)
        return agent.events[-1]

    @staticmethod
    def fail_execution(
        *,
        agent: Agent,
        execution_id: AgentExecutionId,
        reason: str,
    ) -> AgentExecutionFailed:
        reason_vo = FailureReason(value=reason)
        agent.fail_execution(execution_id, reason_vo)
        return agent.events[-1]
