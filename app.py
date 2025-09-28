# Import necessary libraries
import boto3  # AWS SDK for Python
import botocor.config  # For configuring the Boto3 client
import json  # To handle JSON data
import os  # To interact with the operating system (not used here, but good practice)
import sys  # To interact with the Python runtime (not used here, but good practice)
import datetime  # To work with dates and times


def lambda_handler(event, context):
    """
    This is the main entry point for the AWS Lambda function.
    It's triggered by an API Gateway event.
    """
    # Parse the incoming request body from the API Gateway event to get the blog topic
    event = json.loads(event['body'])
    blogtopic = event['blog_topic']

    # Call the function to generate the blog content using AWS Bedrock
    generate_blog = blog_generate_using_bedrock(blogtopic=blogtopic)

    # Check if the blog content was successfully generated
    if generate_blog:
        # Get the current time to create a unique filename
        current_time = datetime.datetime.now().strftime('%H%M%S')
        # Define the S3 object key (the "path" and filename within the bucket)
        s3_key = f"blog_output_folder/{current_time}.txt"
        # Define the target S3 bucket name
        s3_bucket = 'aws_bedrock'
        # Call the function to save the generated blog to S3
        save_blog_details_in_s3(s3_key, s3_bucket, generate_blog)
    else:
        # Print a message to the logs if blog generation failed
        print("No Blog was generated")

    # Return a successful HTTP response to the API Gateway
    return {
        'statusCode': 200,
        'body': json.dumps("Blog Generation is completed")
    }


def blog_generate_using_bedrock(blogtopic: str) -> str:
    """
    Connects to AWS Bedrock to generate a blog post using a foundation model.
    
    :param blogtopic: The topic for the blog post.
    :return: The generated blog content as a string, or an empty string if an error occurs.
    """
    # Create the prompt for the language model, inserting the user's blog topic
    prompt = f"""
    <s>[INST]Human: Write a 500 words blog on the topic {blogtopic}
    Assistant:[/INST]
    """

    # Define the request body with parameters for the model
    body = {
        "prompt": prompt,
        "max_gen_len": 512,      # Maximum number of tokens to generate
        "temperature": 0.5,     # Controls randomness; lower is more deterministic
        "top_p": 0.9            # Controls nucleus sampling
    }

    try:
        # Initialize the Boto3 client for the Bedrock Runtime service
        # It's configured with a longer read timeout and a retry strategy for resilience
        bedrock = boto3.client("bedrock-runtime", region_name="us-east-1",
                               config=botocore.config.Config(read_timeout=300, retries={'max_attempts': 3}))
        
        # Invoke the specified model (Llama 3 8B Instruct) with the request body
        response = bedrock.invoke_model(body=json.dumps(
            body), modelId="meta.llama3-8b-instruct-v1:0")

        # Read the streaming response body from the model
        response_content = response.get('body').read()
        # Parse the JSON response content
        response_data = json.loads(response_content)
        # Extract the generated text from the response
        blog_details = response_data['generation']
        return blog_details
    except Exception as e:
        # Print any errors that occur during the Bedrock API call
        print(f"Error generating the blog:{e}")
        return ""


def save_blog_details_in_s3(s3Key, s3Bucket, generate_blog):
    """
    Saves the generated blog content to a specified S3 bucket.

    :param s3Key: The key (filename and path) for the object in S3.
    :param s3Bucket: The name of the target S3 bucket.
    :param generate_blog: The blog content to be saved.
    """
    # Initialize the Boto3 client for S3
    s3 = boto3.client('s3')
    try:
        # Use put_object to upload the generated blog content to the S3 bucket
        s3.put_object(Bucket=s3Bucket, Key=s3Key, Body=generate_blog)
        print("Successfully saved blog to S3.")
    except Exception as e:
        # Print any errors that occur during the S3 upload
        print(f"Error when saving the code to S3: {e}")