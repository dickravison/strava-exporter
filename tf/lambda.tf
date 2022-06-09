#Create IAM role for Lambda function
resource "aws_iam_role" "strava_exporter" {
  name = "strava_exporter"

  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Effect": "Allow",
      "Sid": ""
    }
  ]
}
EOF

  managed_policy_arns = ["arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"]
  inline_policy {
    name   = "dynamodb_read_write"
    policy = data.aws_iam_policy_document.dynamodb.json
  }
}

data "aws_iam_policy_document" "dynamodb" {
  statement {
    actions   = ["dynamodb:DeleteItem", "dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:Scan", "dynamodb:UpdateItem"]
    resources = [aws_dynamodb_table.strava_data.arn]
  }
}

#Create Lambda function
resource "aws_lambda_function" "strava_exporter" {
  filename         = "../src/strava-exporter.zip"
  function_name    = "strava-exporter"
  role             = aws_iam_role.strava_exporter.arn
  handler          = "get_data.get_access_token"
  source_code_hash = filebase64sha256("../src/strava-exporter.zip")
  runtime          = "python3.9"
  layers           = [data.aws_lambda_layer_version.layer.arn]
  architectures    = ["arm64"]
  timeout          = "60"

  environment {
    variables = {
      DYNAMODB_TABLE = aws_dynamodb_table.strava_data.id
    }
  }

}

#Add permission to Lambda function to allow EventBridge rule to invoke the function
resource "aws_lambda_permission" "allow_eventbridge_pull_data" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.strava_exporter.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.strava_exporter.arn
}


#Create IAM role for Lambda function
resource "aws_iam_role" "dynamodb_stream" {
  name = "strava_dynamodb_stream"

  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Effect": "Allow",
      "Sid": ""
    }
  ]
}
EOF

  managed_policy_arns = ["arn:aws:iam::aws:policy/service-role/AWSLambdaDynamoDBExecutionRole"]
  inline_policy {
    name   = "dynamodb_update"
    policy = data.aws_iam_policy_document.dynamodb_update.json
  }
}

data "aws_iam_policy_document" "dynamodb_update" {
  statement {
    actions   = ["dynamodb:UpdateItem"]
    resources = [aws_dynamodb_table.strava_data.arn]
  }
}

#Create Lambda function
resource "aws_lambda_function" "process_stream" {
  filename         = "../src/strava-process-stream.zip"
  function_name    = "strava-process-stream"
  role             = aws_iam_role.dynamodb_stream.arn
  handler          = "process_stream.lambda_handler"
  source_code_hash = filebase64sha256("../src/strava-process-stream.zip")
  runtime          = "python3.9"
  layers           = [data.aws_lambda_layer_version.layer.arn]
  architectures    = ["arm64"]
  timeout          = "120"

  environment {
    variables = {
      DYNAMODB_TABLE = aws_dynamodb_table.strava_data.id
    }
  }
}

#Add event source mapping to invoke this function when there is an INSERT into DynamoDB
resource "aws_lambda_event_source_mapping" "dynamodb" {
  event_source_arn  = aws_dynamodb_table.strava_data.stream_arn
  function_name     = aws_lambda_function.process_stream.arn
  starting_position = "LATEST"

  filter_criteria {
    filter {
      pattern = jsonencode({
        eventName : ["INSERT"]
      })
    }
  }
}

#Create IAM role for Lambda function
resource "aws_iam_role" "strava_notifier" {
  name = "strava_notifier"

  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Effect": "Allow",
      "Sid": ""
    }
  ]
}
EOF

  managed_policy_arns = ["arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"]
  inline_policy {
    name   = "dynamodb_query"
    policy = data.aws_iam_policy_document.dynamodb_query.json
  }
  inline_policy {
    name   = "sns_publish"
    policy = data.aws_iam_policy_document.sns_publish.json
  }
}

data "aws_iam_policy_document" "dynamodb_query" {
  statement {
    actions   = ["dynamodb:Query"]
    resources = [aws_dynamodb_table.strava_data.arn, "${aws_dynamodb_table.strava_data.arn}/*"]
  }
}

data "aws_iam_policy_document" "sns_publish" {
  statement {
    actions   = ["sns:Publish"]
    resources = [var.sns_topic]
  }
}

#Create Lambda function
resource "aws_lambda_function" "strava_notifier" {
  filename         = "../src/strava-notifier.zip"
  function_name    = "strava-notifier"
  role             = aws_iam_role.strava_notifier.arn
  handler          = "notification.lambda_handler"
  source_code_hash = filebase64sha256("../src/strava-notifier.zip")
  runtime          = "python3.9"
  layers           = [data.aws_lambda_layer_version.layer.arn]
  architectures    = ["arm64"]
  timeout          = "60"

  environment {
    variables = {
      DYNAMODB_TABLE = aws_dynamodb_table.strava_data.id
      SNS_TOPIC      = var.sns_topic
    }
  }

}

#Add permission to Lambda function to allow EventBridge rule to invoke the function
resource "aws_lambda_permission" "allow_eventbridge_weekly_notifier" {
  statement_id  = "AllowWeeklyExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.strava_notifier.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.weekly_notifier.arn
}

resource "aws_lambda_permission" "allow_eventbridge_monthly_notifier" {
  statement_id  = "AllowMonthlyExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.strava_notifier.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.monthly_notifier.arn
}
