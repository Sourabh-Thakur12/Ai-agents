from typing import Dict, Any
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from .models import CompanyAnalysis, CompanyInfo, ResearchState
from .prompts import DeveloperToolsPrompts
from .firecrawl import FirecrawlService


class Workflow:
    def __init__(self):
        self.firecrawl = FirecrawlService()
        self.llm = ChatGoogleGenerativeAI(
            model = "gemini-2.5-flash",
            temperature = 0.1,)
        
        self.prompts = DeveloperToolsPrompts()
        self.workflow = self._build_workflow()

    def _build_workflow(self):
        graph = StateGraph(ResearchState)
        graph.add_node("extract_tools", self._extract_tools_step)
        graph.add_node("research", self._research_step )
        graph.add_node("analyze", self._analyze_step)
        graph.set_entry_point("extract_tools ")
        graph.add_edge("extract_tools", "research")
        graph.add_edge("research", "analyze")
        graph.add_edge("analyze", END)
        return graph.compile()

    def _extract_tools_step(self, state: ResearchState) -> Dict[str, Any]:
        print(f"🔍 Finding articles about: {state.query}")
        
        article_query = f"{state.query} tools comparison best alternatives"
        search_results = self.firecrawl.search_companies(article_query, num_results=3)
        
        
        all_content = ""
        for result in search_results:
            url = result.get("uel","")
            scraped = self.firecrawl.scrape_company_pages(url)
            if scraped:
                all_content += scraped.markdown[:1500] + "\n\n"
                
                
        messages = [
            SystemMessage(content = self.prompts.extract_tools_system_prompt),
            HumanMessage(content = self.prompts.tool_extraction_user(state.query, all_content))
        ]
        
        try:
            response = self.llm.invoke(messages)
            tool_names = [
                name for name in response.content.strip().split("\n")
                if name.strip()
            ]
            print(f"extracted tools:{', '.join(tool_names)}")
            return{"extracted_tools": tool_names}
        except Exception as e:
            print(f"Error during tool extraction: {e}", [])


    def _analyze_company_content(self, company_name:str, content:str) -> CompanyAnalysis:
        structured_llm = self.llm.with_structured_output(CompanyAnalysis)
        
        messages = [
            SystemMessage(content = self.prompts.TOOL_ANALYSIS_SYSTEM_PROMPT),
            HumanMessage(content = self.prompts.tool_analysis_user(company_name, content))
        ]
        
        try:
            analysis = structured_llm.invoke(messages)
            return analysis
        except Exception as e:
            print(e)
            return CompanyAnalysis(
                pricing_model= "unknown",
                is_open_source=None,
                tech_stack=[],
                description="failed",
                api_available=None,
                language_support=[],
                integration_capabilities=[],
            )

    def _research_step(self, state:ResearchState) -> Dict[str, Any]:
        extracted_tools = getattr(state, "extracted_tools", [])
        
        if not extracted_tools:
            print("No tools extracted, skipping research step")
            search_results = self.firecrawl.search_companies(state.query, num_results=3)
            tool_name =[
                result.get("metadata", {}).get("title", "Unknown Tool")
                for result in search_results.data
            ]

        else:
            tool_name = extracted_tools[:4]
            
        print(f"Researching {len(tool_name)} tools: {', '.join(tool_name)}")
        
        companies = []
        for  tools in tool_name:
            tool_search_reslts = self.firecrawl.search_companies(tool_name + "official site" , num_sults= 1)
            
            if tool_search_reslts:
                result = tool_search_reslts.data[0]
                url = result.get("uel", "")
                
                company = CompanyInfo(
                    name=tools,
                    description=result.get("markdown", ""),
                    website=url,
                    tech_stack=[],
                    competetitors=[],
                )
                
                scraped = self.firecrawl.scrape_company_pages(url)
                if scraped:
                    content = scraped.markdoown
                    analysis = self._analyze_company_content(company.name, content)
                    

                    company.pricing_model = analysis.pricing_model
                    company.is_open_source = analysis.is_open_source
                    company.tech_stack = analysis.tech_stack
                    company.description = analysis.description
                    company.api_available = analysis.api_availabe
                    company.language_support = analysis.language_support
                    company.integration_capablities = analysis.integration_capablities
                    
                companies.append(company)
                
            return {
                "companies": companies,
            }

    def _analyze_step(self, state= ResearchState) -> Dict[str, Any]:
        print("Generating Results")
        
        company_data = ",".join([
            company.model_dump_json() for company in state.companies
        ])

        messages= [
            SystemMessage(content = self.prompts.ANALYSIS_SYSTEM_PROMPT),
            HumanMessage(content = self.prompts.analysis_user(state.querry, company_data))
        ]

        response = self.llm.invoke(messages)
        return {"analysis": response.content}

    def run(self, query: str) -> ResearchState:
        initial_state = ResearchState(query=query)
        final_state = self.workflow.invoke(initial_state)
        return ResearchState(**final_state)