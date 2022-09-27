#Create Eventbridge rule to invoke Lambda function each day at specific time
resource "aws_cloudwatch_event_rule" "strava_exporter" {
  name        = "${var.project_name}-strava-exporter"
  description = "Rule to invoke bus notifier function"

  schedule_expression = var.strava_exporter_cron
}

#Link Eventbridge rule to Lambda function
resource "aws_cloudwatch_event_target" "strava_exporter" {
  rule      = aws_cloudwatch_event_rule.strava_exporter.name
  target_id = "export-strava-data"
  arn       = aws_lambda_function.strava_exporter.arn
  input     = "{\"USER\":\"${var.username}\"}"
}

#Create Eventbridge rule to invoke Lambda function weekly
resource "aws_cloudwatch_event_rule" "weekly_notifier" {
  name        = "${var.project_name}-weekly-stats"
  description = "Rule to invoke Strava stats notifier function for the past weeks data"

  schedule_expression = var.weekly_cron
}

#Link Eventbridge rule to Lambda function
resource "aws_cloudwatch_event_target" "weekly_notifier" {
  rule      = aws_cloudwatch_event_rule.weekly_notifier.name
  target_id = "strava-weekly-stats"
  arn       = aws_lambda_function.strava_notifier.arn
  input     = "{\"USER\":\"${var.username}\"}"
}

#Create Eventbridge rule to invoke Lambda function monthly
resource "aws_cloudwatch_event_rule" "monthly_notifier" {
  name        = "${var.project_name}-monthly-stats"
  description = "Rule to invoke Strava stats notifier function for the past months data"

  schedule_expression = var.monthly_cron
}

#Link Eventbridge rule to Lambda function
resource "aws_cloudwatch_event_target" "notifier" {
  rule      = aws_cloudwatch_event_rule.monthly_notifier.name
  target_id = "strava-monthly-stats"
  arn       = aws_lambda_function.strava_notifier.arn
  input     = "{\"USER\":\"${var.username}\"}"
}
