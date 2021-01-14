# github_integration
github_integration is a python project to load data from GitHub and store in Snowflake datawarehouse.

**GITHUB

The Source of the data is GitHub. 

There was a requirement to get information regarding pull requests and accociated files. 
According to above, let's put some details about Pull request from GitHub.

1. States: Open/Closed/Merged 
2. Pull Request can consists or not consists of Commits.
   Commits associate with Files, which were changed. But in this task we are interesting in 
   number of Files by Pull Request, so we will not use Commit in the model to simplify that.
3. Pull Request can consists or not consists of Files.
4. Pull Request with lower ID can be merged after Pull Request with higher ID. 
   To track this we can use: Pull Request Updated Time.    
	
**The main goals during development were:

1. Performance 
2. Reduce GitHub API call
2. Simple model
3. Reloading process

To achive above goals, there was a decision to use GraphQL GitHub API. 

**There are 2 types of GraphQL queries will be running:

PullRequests query:

1. All details about pull requests.
2. Pagination of all pull requests.
3. Files related information and pagination across files.

PullRequest query:

1. All details about exact pull request.
2. This query will be used, when app will need to use pagination across files.

**Communication workflow with GitHub API:

1. Query API for first chunk (query limit is 100) of Pull Requests.
2. Process first Pull Request: get Pull Request Details, get Files details.
3. Query API for rest chunks of Files, if number of Files are more then query limit (100), etc.
4. Process rest Pulls requests from the first chunk.
5. Go to the step 1, for the next chunk of Pull Requests.

**Snowflake data warehouse:

There was been set up simple data model, using snowflake-sqlalchemy ORM:

PullRequests - unique dictionary of Pull Requests with corresponding attributes.
PullRequestsFiles - Pull Requests with corresponding list of Files. Pull Request can have multiple Files.
                    Files can be present in multiple Pull Request.
					
There is one-to-many relationship set up between PullRequests and PullRequestsFiles Table.

**Upload history/Upload latest

Before running data from GitHub to Snowflake, app will take 2 values from Snowflake:

maximum Pull Request ID
latest Pull Request updated time

**If Model has no data yet, those will be set to 0 and "1970-01-01".

1. Requesting data from GitHub, app will always check for the Pull Requests with:
   Id > maximum Pull Request ID OR
   Updated Time > latest Pull Request updated time
   
2. During working with Snowflake Session, app will descibe add or merge objects to the session, 
   depends on above condition.  




