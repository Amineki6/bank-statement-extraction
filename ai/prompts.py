def get_basic_account_info_prompt() -> str:
    """
    Prompt for fetching basic account info from the pdf file.
    :return:
    """
    return """
    You are an AI assistant assisting the german bankers in digitizing scans and faxes of bank transactions.
    You are provided with the following image, which may contain information about the customer's account data.
    Return the account data in the following format:

    ```json
    {
        account_data: {
            'name': 'Customer Name **Required**',
            'IBAN': 'IBAN number **Required**',
            'document_date': 'Date the document was issues **Required**',
            'previous_account_balance': 'Previous account balance, **Required**','
            'new_account_balance': 'Account balance, **Required**'
        }
    }
    ```
    
    IF NOT ACCOUNT DATA IS AVAILABLE ON THE PAGE, RETURN AN EMPTY DICTIONARY:
    ```json
    {
        'account_data': {}
    }
    ```
    
    # How to respond to this prompt: - response_format: JSON 
    # The JSON should be parseable using a single json.loads in python. RETURN NO FURTHER TEXT, JUST THE JSON.
    """


def get_transactions_prompt() -> str:
    """
    Prompt for fetching bank transactions from the pdf page image.
    :return: the prompt.
    """
    return """
    You are an AI assistant assisting the german bankers in digitizing scans and faxes of bank transactions.
    You are provided with the following image, which may contain multiple bank transactions.
    Return a json response in the following format:
    
    ```json
    {
        'transactions': [
            {
                'date': 'Transaction date, **always required**.',
                'amount': 'Transaction amount, **always required**.',
                'transaction_text': 'Transaction text, if available.'
            }
        ]
    }
    
    IF NOT TRANSACTIONS ARE AVAILABLE, RETURN THE ARRAY:
    
    ```json
    {
        'transactions': []
    }
    ```
    
    # How to respond to this prompt: - response_format: JSON 
    # The JSON should be parseable using a single json.loads in python. RETURN NO FURTHER TEXT, JUST THE JSON.
    ```
    """
