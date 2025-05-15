from openai import OpenAI
import mysql.connector
from mysql.connector import Error
import time
import json
from fastapi import FastAPI, HTTPException, Query, Form,Request
from fastapi.responses import FileResponse
from pydantic import BaseModel
import os
# Initialize the OpenAI client
api_key=os.environ.get('OPENAI_API_KEY')
client = OpenAI(api_key=api_key)

def execute_sql_query(query):
    result=''
    db_details={
    'host':'localhost',
    'user':'shanu',
    'password':'shanu25',
    'database':'text2sql'

}
    try:
        conn = mysql.connector.connect(**db_details)
      
        cursor = conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
        

        columns = [column[0] for column in cursor.description]
                    # Create a dictionary with 'columns' and 'data' keys
        formatted_results = {
                        'columns': columns,
                        'rows': rows
                    }
       # result=json.dumps(formatted_results, default=str)

        result=formatted_results

        return result,True
    except mysql.connector.Error as Err:
        return '',Err



tables_info='''

table name : employees
    columns: 
    emp_id  - stores employee id
    emp_name - full name of employee
    emp_salary - salary of employee
    department - dempartment of employee example sales,accounting,marketing,development
    job_title - job title of employee example manager,software engineer,accountant,marketing manager,designer
    emp_email - email of employee
    joining_date - employee joining date
    emp_status - status of employee example active,inactive

    
table name : sales
    columns:
    product_id - id of product
    price - price of product sold
    lead_id - id of employee who sold the projuct
    sale_date - date of sale
    sale_type - how product was sold example e-commerce,on-site
    sale_status - status of sale example pending,completed,cancelled



table name : products 
    columns:
    product_id - id of product
    product_name - name of product
    product_price - cost or price for productd
    in_stock - number of units of product for available for sale


'''


execute_sql_function = {
    "name": "execute_sql_query",
    "description": "Execute a SQL query on MySQL database and returns true if query executed sucessfully else on error returns the error statement",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The SQL query to execute"
            }
        },
        "required": ["query"]
        
    }
}




assistant = client.beta.assistants.create(
    name="text to sql bot",
    instructions=f'''You are a SQL expert. Given an input question, create a syntactically correct mySQL query to run and return ONLY the generated Query and nothing else. 
                    the details of tables is as follows {tables_info}.
                    
                    for correct query generation you must follow these instructions.
                    the SQL query must not include statements such as INSERT,DELETE,UPDATE,TRUNCATE,DROP,ALTER. 
                    Pay close attention to the filtering criteria mentioned in the question and incorporate them using the WHERE clause in your SQL query
                    do not create SQL queries that modify the data.
                    return just the SQL query no extra text or comment.
                    if the question asks very few details include a few relevant fields or information appropriately.
                    if any of the questions voilate the instructions return a short user friendly message . i am a data analysis ai i cannot help you with that task try asking something else.
                    only the sql statement must be returned without any comments and annotations.
                    use dynamic values for current date.
                    Unless explicitly specified do not include more than 15 rows while fetching data.
                    use user friendly aliases for the column names
                    create queries using the tables information prvided to fulfill the questions asked.
                    you can use all information to answer the queries
                    to answer the questions asked by user sql query must be created and execute_sql_query function must be called.

                    if a correct SQL query is generated then the execute_sql_query function must be called with the sql statemet as a parameter,
                    if the returned result is an error or exception fix the error by rebuilding the query and call the execute_sql_query function again.
                    for a successful execution True is returned as result.
     
                    after the sql query executed  an output is generated for a end user summarizing the details . you can only reveal you identity as a data Analysis ai an you help in fetching and getting insights from data.
                     
                    do not include sql statements in text response only send them using tool call with execute_sql_query 
                    if the response to question has points and lists format the text example using  bullet points.
                    always use execute_sql_query function to fetch the results of the query
                    for every query asked by the user try to execute a sql query.
                    IMPORTANT INSTRUCTIONS:
                    do not hide anything from the user. Always give full information to the user. 
                    user should never be blind sighted over any information.
                    i said never. let the user know what it is
      ''',
    model="gpt-4o",
    tools=[{"type": "function", "function": execute_sql_function}]
)

# Create a thread
thread = client.beta.threads.create()

def chat_with_assistant(user_input):
    query_status=None
    query_result=None
    # Add a message to the thread
    client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=user_input
    )

    # Run the assistant
    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant.id
    )


    # Wait for the assistant to complete its response
    runstart=time.time()
    while run.status != 'completed':
        print(run.status)
        time.sleep(0.5)


        if run.status=='failed':
             print('Failed')
             print('error')
             print(run.last_error)
             return {'type':'text','data':'Request could not be completed try again'}

        run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)

        if run.status=='requires_action':

            for tool_call in run.required_action.submit_tool_outputs.tool_calls:
                print('tool call for',tool_call.function.name)
                #submiting the query execution error or success to tool call
                if tool_call.function.name=='execute_sql_query':
                    query=json.loads(tool_call.function.arguments)['query']
                    query_result,query_status=execute_sql_query(query)
                    client.beta.threads.runs.submit_tool_outputs(
                        thread_id=thread.id,
                        run_id=run.id,
                        tool_outputs=[{
                            'tool_call_id':tool_call.id,
                            'output':str(query_status)
                            }])
        
    
    print('run took',round(time.time()-runstart),'s')
    response={'messages':[]}
    if query_status==True:
        response['messages'].append({'type':'table','data':query_result})
    
    # Retrieve the messages  for debugging
    messages = client.beta.threads.messages.list(thread_id=thread.id)
    if messages.data and (len(messages.data) > 0):
        bot_response=messages.data[0].content[0].text.value
        response['messages'].append({'type':'text','data':bot_response})
    

    # Return the assistant's response
    #return messages.data[0].content[0].text.value
    return response






 #  cli loop 
'''
# Main chat loop
print("Chatbot: Hello! How can I assist you today?")
while True:
    user_input = input("You: ")
    if user_input.lower() in ['exit', 'quit', 'bye']:
        print("Chatbot: Goodbye!")
        break
    response = chat_with_assistant(user_input)
    print("Chatbot:", response)

# Clean up
client.beta.assistants.delete(assistant.id)

'''







app = FastAPI()

class Prompt(BaseModel):
    text: str

@app.get("/")
async def read_root():
    return FileResponse('./indexgpt.html')


@app.get("/newConversation")
async def new_conversation():
    print('creating new Thread')
    global thread
    client.beta.threads.delete(thread_id=thread.id)
    thread = client.beta.threads.create()    
    return 'ok'



@app.post("/sendPrompt")
async def send_prompt(request: Request ):
    try:
        # Process the prompt here
        body = await request.json()
        
        # Access the 'prompt' key directly
        prompt = body.get("prompt")

        if prompt=='test':
            text={'type':'text','data':'Here is the information that you asked'}
            table={"type":"table","data":{"columns":["Name","Age","City","Occupation","Salary"],"rows":[["John Doe",28,"New York","Engineer",70000],["Jane Smith",34,"Los Angeles","Designer",85000],["Michael Brown",42,"Chicago","Manager",95000],["Emily Davis",29,"Houston","Developer",72000],["David Wilson",37,"Miami","Consultant",88000],["Sarah Johnson",31,"San Francisco","Architect",93000],["Chris Lee",45,"Seattle","Scientist",100000],["Jessica Taylor",26,"Boston","Data Analyst",68000],["James Martin",40,"Denver","Lawyer",110000],["Laura Garcia",33,"Phoenix","Doctor",120000]]}}
        
            return {'messages':[text,table]}
        
        response=chat_with_assistant(prompt)

        return response
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))





if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)