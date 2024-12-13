def config_graph(model, api_key, base_url):
    import sys
    import os
    #ensure we are operating from the project directory, one step above src
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from langchain_core.messages import ToolMessage
    from langchain_mistralai import ChatMistralAI
    from langchain_anthropic import ChatAnthropic
    from langchain_ollama.chat_models import ChatOllama
    from langchain_openai import ChatOpenAI
    from typing import Annotated, TypedDict
    from langgraph.graph import StateGraph, START, END
    from langgraph.graph.message import add_messages, AnyMessage
    from langgraph.prebuilt import ToolNode, tools_condition
    from dotenv import load_dotenv
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.prompts import MessagesPlaceholder
    import sys
    from langchain_core.prompts import ChatPromptTemplate
    from typing_extensions import TypedDict
    from langchain_core.messages import ToolMessage
    from langchain_core.runnables import RunnableLambda, Runnable, RunnableConfig
    from langgraph.checkpoint.memory import MemorySaver
    from tools.find_protocols import find_protocols
    from tools.analyze_packet import analyze_packet
    from tools.find_router import find_router
    from tools.ip_mac import ip_mac
    from tools.subnet import subnet
    from tools.tcp_session import tcp_session
    from typing import List

    #load the keys from BASE_DIR which is just the packto.ai project directory
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    #environment variables
    # mistral_key = os.getenv('MISTRAL_API_KEY')
    
    if (model == "Mistral"):
        os.environ['MISTRAL_API_KEY'] = api_key
        print("MISTRAL")
        llm = ChatMistralAI(model="mistral-large-latest", temperature=0)
    elif (model == "Anthropic"):
        print("ANTHRO")
        os.environ["ANTHROPIC_API_KEY"] = api_key
        print("ANTHROPIC")
        llm = ChatAnthropic(model="claude-3-5-sonnet-20240620")
    elif (model == "OpenAI"):
        os.environ['OPENAI_API_KEY'] = api_key
        llm = ChatOpenAI(model="gpt-4o")
    else:
        if not base_url.startswith("http://") and not base_url.startswith("https://"):
            base_url = "http://" + base_url
        base_url = base_url.replace("localhost", "host.docker.internal")
        if (api_key):
            llm = ChatOpenAI(base_url=base_url, api_key=api_key)
        else:
            llm = ChatOpenAI(base_url=base_url, api_key="not-needed")

    #This is the prompt we use to tell the LLM its job. We can pass a group of PCAPs in and use anything we want as external_context
    primary_assistant_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a helpful customer support assistant for analyzing packet traces. "
                " Use the provided tools to search for protocols, security threats, and other information to assist the user's queries. "
                " When searching, be persistent. Expand your query bounds if the first search returns no results. "
                " If a search comes up empty, expand your search before giving up."
                " Use {PCAPs} as the group of files to analyze."
            ),
            MessagesPlaceholder("messages"),
        ]
    )

    #put all the tools we've made in an array and bind them to the LLM
    tools = [find_protocols, analyze_packet, find_router, ip_mac, subnet, tcp_session]
    llm_with_tools = llm.bind_tools(tools)

    #LangGraph has things called runnables which are what we use to invoke essentially. It is basically a class that has functions to use the LLLM.
    #We want this class to include the llm with tools bound to it and use the prompt we made to answer questions when we invoke upon this runnable
    packto_runnable = primary_assistant_prompt | llm_with_tools

    """
    Define graph state
    This makes it so that every message will be in a list
    and all of those messages will be received to every node
    in the graph when it is called. Nodes are basically just 
    functions. So those functions will be called and they will 
    receive messages state as input
    """
    class AgentState(TypedDict):
        messages: Annotated[list[AnyMessage], add_messages]#Annotated[Sequence[BaseMessage], operator.add]
        PCAPs: List[str]
        external_context: dict

    class Assistant:
        def __init__(self, runnable: Runnable):
            self.runnable = runnable
        def __call__(self, state, config: RunnableConfig):
                while True:
                    configuration = config.get("configurable", {})
                    user_id = configuration.get("user_id", None)
                    state = {**state, "user_info": user_id}
                    result = self.runnable.invoke(state)
                    # Re-prompt if LLM returns an empty response
                    if not result.tool_calls and (
                        not result.content
                        or isinstance(result.content, list)
                        and not result.content[0].get("text")
                    ):
                        messages = state["messages"] + [("user", "Respond with a real output.")]
                        state = {**state, "messages": messages}
                    else:
                        break
                return {"messages": result}
        
    def handle_tool_error(state) -> dict:
        """
        Function to handle errors that occur during tool execution.
        
        Args:
            state (dict): The current state of the AI agent, which includes messages and tool call details.
        
        Returns:
            dict: A dictionary containing error messages for each tool that encountered an issue.
        """
        # Retrieve the error from the current state
        error = state.get("error")
        
        # Access the tool calls from the last message in the state's message history
        tool_calls = state["messages"][-1].tool_calls
        
        # Return a list of ToolMessages with error details, linked to each tool call ID
        return {
            "messages": [
                ToolMessage(
                    content=f"Error: {repr(error)}\n please fix your mistakes.",  # Format the error message for the user
                    tool_call_id=tc["id"],  # Associate the error message with the corresponding tool call ID
                )
                for tc in tool_calls  # Iterate over each tool call to produce individual error messages
            ]
    }

    def create_tool_node_with_fallback(tools: list) -> dict:
        """
        Function to create a tool node with fallback error handling.
        
        Args:
            tools (list): A list of tools to be included in the node.
        
        Returns:
            dict: A tool node that uses fallback behavior in case of errors.
        """
        # Create a ToolNode with the provided tools and attach a fallback mechanism
        # If an error occurs, it will invoke the handle_tool_error function to manage the error
        return ToolNode(tools).with_fallbacks(
            [RunnableLambda(handle_tool_error)],  # Use a lambda function to wrap the error handler
            exception_key="error"  # Specify that this fallback is for handling errors
        )

    """
    Here we make the graph by setting up the state
    We set the entry point to the agent (the LLM) itself
    and then after th agent interprets the question,
    it calls a tool, then the conditional edge
    decides if the question has been sufficiently 
    answered. If not, keep calling tools.
    """
    workflow = StateGraph(AgentState)
    workflow.add_node("agent", Assistant(packto_runnable))
    workflow.add_node("tools", create_tool_node_with_fallback(tools))
    workflow.add_edge(START, "agent")
    workflow.add_conditional_edges("agent", tools_condition)
    workflow.add_edge("tools", "agent")

    #holds on the memory within a session so we can keep it in graph state for the database. This isn't entirely necessary but I like it for extra 
    #assurance that interactions with Packto will be saves
    memory = MemorySaver()

    print("WAHHHHH")

    #finally make the graph
    graph = workflow.compile(checkpointer=memory)

    return graph