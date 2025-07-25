1. @DEVELOPMENT-PLAN.md
2. 

You are a professional prompt engineer with deep experience. 

Carefully analyze the context below, translate the plan objectives into actionable requests, then generate a prompt that imply doing the suggested tasks, tasking the AI. 
Your primary goal in this scenario is to take a piece of human-readable project context (like conclusions, plans, or recommendations) and translate it into a prompt that guides or directs an AI code assistant towards actionable tasks using its available tools, The output should imply or set up these actions, rather than just summarizing the context conversationally. Implement these changes directly.


I had Cursor (in the old express app) generate a detailed explanation of the core parts of the application (I focused on one very heavy endpoint). I told it that this was going to be provided to a team working on migrating to NestJS. I had it saved as an md file in the project.

I copied that md file into the new nestjs project and then had Cursor in read that file. I then asked it to generate a detailed implementation plan and save it to a new md file in the project.

I spent the next 2 days having Cursor just execute that implementation plan and generate new documentation as it went along.

So now I have a markdown file that documents the migration, a document that documents the implementation steps and another that documents the new code.

It was super helpful.

It has become a new process for me. Any time I work on something, I have Cursor updte the docs for that code to keep logic and docs aligned.


