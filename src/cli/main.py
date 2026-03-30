import asyncio
import uuid

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from langgraph.types import Command

from src.config import config
from src.agent.graph import graph

console = Console()


async def run_cli() -> None:
    config.validate()
    thread_id = str(uuid.uuid4())
    graph_config = {"configurable": {"thread_id": thread_id}}

    console.print(
        Panel(
            "[bold green]Twenty CRM Agent[/bold green]\n"
            "Ask questions about your CRM data in natural language.\n"
            "Type [bold]exit[/bold] to quit.",
            title="Welcome",
            border_style="green",
        )
    )

    while True:
        user_input = Prompt.ask("\n[bold cyan]You[/bold cyan]")
        if user_input.strip().lower() in ("exit", "quit", "q"):
            console.print("[dim]Goodbye![/dim]")
            break

        with console.status("[bold yellow]Thinking...[/bold yellow]"):
            result = await graph.ainvoke(
                {"messages": [{"role": "user", "content": user_input}]},
                config=graph_config,
            )

        # Check for HITL interrupt
        state = graph.get_state(graph_config)
        while state.next:
            # There's a pending interrupt (mutation approval)
            for task in state.tasks:
                if hasattr(task, "interrupts") and task.interrupts:
                    for intr in task.interrupts:
                        payload = intr.value
                        if isinstance(payload, dict) and payload.get("type") == "mutation_approval":
                            console.print(
                                Panel(
                                    Markdown(payload["description"]),
                                    title="[bold red]Mutation Approval Required[/bold red]",
                                    border_style="red",
                                )
                            )
                            choice = Prompt.ask(
                                "Approve this operation?",
                                choices=["yes", "no"],
                                default="no",
                            )
                            resume_value = "approved" if choice == "yes" else "rejected"

                            with console.status("[bold yellow]Executing...[/bold yellow]"):
                                result = await graph.ainvoke(
                                    Command(resume=resume_value),
                                    config=graph_config,
                                )

            state = graph.get_state(graph_config)

        # Extract and display the final response
        messages = result.get("messages", [])
        if messages:
            last = messages[-1]
            content = last.content if hasattr(last, "content") else str(last)
            if content:
                console.print()
                console.print(
                    Panel(
                        Markdown(content),
                        title="[bold green]Agent[/bold green]",
                        border_style="blue",
                    )
                )


def main() -> None:
    asyncio.run(run_cli())


if __name__ == "__main__":
    main()
