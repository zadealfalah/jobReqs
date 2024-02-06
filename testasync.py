import tech_pipeline
import asyncio

filename = fr"C:\Users\Zade\Desktop\PythonStuff\jobReqs\jobReqs\indscraper\indscraper\spiders\data\test_replace_06_02_2024_processed.json"
pipeline = tech_pipeline.TechIdentificationPipeline(filename)

async def main():
    # Preprocess the data and select relevant text sections
    pipeline.select_relevant_text()

    # Get technology responses from GPT
    await pipeline.fetch_gpt_techs()

# Run the main entry point of your program
if __name__ == "__main__":
    asyncio.run(main())