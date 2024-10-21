This API is built to interact with the "Automated Fact Checker" program.

Includes a Python/Flask API designed to be hosted on an AWS EC2 instance.

It accepts HTTP GET requests to <IP>/check with params url & phrase.

This GET request will return a JSON object containing all of the identified claims within the article/Youtube video of the given URL that relate to the given phrase.
Each claim will be accompanied by three sources, as well as an assessment of if the sources support the claim.
The format is as follows:
{
  {success: true} 
  {claim: "Claim 1", sources: ["Source URL 1", "Source URL 2", "Source URL 3"], rating: "Assessment"} 
  {claim: ... }
}
