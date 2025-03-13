#!/usr/bin/env python3
import base64
import json
import os
import time
import random

from typing import List, Tuple
from openai import RateLimitError
from langchain.callbacks import get_openai_callback
from langchain.chat_models import AzureChatOpenAI
from langchain.schema import HumanMessage

import setup
from log_handling import log_handler
from log_handling.log_handler import Logger, Module

logger: Logger = log_handler.get_instance()


class AzureOpenAIAdapter:
    """
    Handles the Azure OpenAI connection
    """
    CONFIG: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')

    @staticmethod
    def __remove_text_before_json(gpt_response: str) -> str:
        """
        Removes any text and comments before a json response from gpt.
        :param gpt_response: gpt's response.
        :return: the filtered response.
        """
        if '{' not in gpt_response or '}' not in gpt_response:
            return gpt_response
        idx = gpt_response.index('{')
        gpt_response = (gpt_response[idx:])[::-1]
        idx = gpt_response.index('}')
        gpt_response = (gpt_response[idx:])[::-1]
        return gpt_response

    @staticmethod
    def __remove_text_after_json(gpt_response: str) -> str:
        """
        Remove trailing comment after json response from GPT.
        :param gpt_response: response from gpt api.
        :return: the cleaned response.
        """
        index_of_brace = gpt_response.find("`")
        if index_of_brace != -1:
            gpt_response = gpt_response[:index_of_brace + 1]
        return gpt_response

    @staticmethod
    def __load_configs(config_file_path: str):
        """
        Load the azure chatbot configs from the provided file.
        :param config_file_path: path to the json configs file.
        :return: the configs as a json object.
        """
        with open(config_file_path) as config_file:
            return json.load(config_file)

    def __llm_init(self) -> AzureChatOpenAI:
        """
        Load the azure chatbot configs and return the LLM objects.
        :return: the azure chatbot instance.
        """
        configs = self.__load_configs(config_file_path=self.CONFIG)
        openai_api_key: str = setup.OPENAI_API_KEY
        openai_api_base: str = configs['OPENAI_API_BASE']
        openai_api_version: str = configs['OPENAI_API_VERSION']
        deployment_name: str = configs['DEPLOYMENT_NAME']
        openai_api_type: str = "azure"

        if not openai_api_key:
            logger.error('OpenAI Key missing!')
            raise Exception()

        return AzureChatOpenAI(
            openai_api_base=openai_api_base,
            openai_api_version=openai_api_version,
            deployment_name=deployment_name,
            openai_api_key=openai_api_key,
            openai_api_type=openai_api_type,
        )

    def __init__(self):
        """
        Creates the azure chatbot instance.
        :return: the azure chatbot instance.
        Exits on error.
        """
        try:
            logger.debug('Creating azure chatbot instance...', module=Module.AZR)
            self.llm: AzureChatOpenAI = self.__llm_init()
            logger.debug('Azure chatbot initialised.', module=Module.AZR)
        except Exception as e:
            logger.error('Error creating azure chatbot - Configurations missing. Terminating.', module=Module.AZR)
            logger.debug('Trace:', e, module=Module.AZR)
            exit(-1)

    @staticmethod
    def __debug_cost(response, cb) -> None:
        logger.debug(response, module=Module.AZR)
        logger.debug(f"Total Cost (USD): ${format(cb.total_cost, '.6f')}", module=Module.AZR)

    @staticmethod
    def __get_image_data(image_uri: str) -> Tuple[str, str]:
        """
        Get the encoded image data and the image type as a tuple.
        :param image_uri: uri to the image on the file system.
        :return: the encoded image data and the image type.
        """
        image_data = base64.b64encode(open(image_uri, 'rb').read()).decode('ascii')
        image_type = 'jpg'
        if '.png' in image_uri:
            image_type = 'png'
        elif '.jpeg' in image_uri:
            image_type = 'jpeg'
        return image_data, image_type

    def __build_llm_template(self, template: str, image_uri: str) -> List:
        """
        Set the llm response type and data format.
        :return: the llm properties as a list.
        """
        content = [{"type": "text", "text": template}]
        if len(image_uri) and image_uri.strip() != '':
            image_data, image_type = self.__get_image_data(image_uri=image_uri)
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/{image_type};base64,{image_data}"},
            })
        return [
            HumanMessage(
                content=content,
                response_format={
                    "type": "json_object"
                },
            )
        ]

    @staticmethod
    def __wait_for_retry() -> None:
        """
        Waits 2-3 seconds on azure rate limit error.
        :return:
        """
        # Azure recommends waiting at least 1 second before retrying
        wait_time: float = 2 + random.uniform(0, 1)
        logger.warning(f"Rate limit error encountered. Retrying in {wait_time} second...", module=Module.AZR)
        time.sleep(wait_time)

    def ask_openai(self, template: str, image_uri: str = '', max_retries: int = 10):
        """
        Send a prompt to the llm model.
        :param template: the text template to use.
        :param image_uri: file system uri to an image to include in the AI request.
        :param max_retries: the maximum number of retries in case of rate limit error.
        :return: the llm's response as json.
        """
        retries = 0
        while retries <= max_retries:
            try:
                with get_openai_callback() as cb:
                    response = self.llm(self.__build_llm_template(template=template, image_uri=image_uri))
                    response = self.__remove_text_before_json(gpt_response=response.content)
                    response = self.__remove_text_after_json(gpt_response=response)
                    self.__debug_cost(response=response, cb=cb)
                    return response
            except RateLimitError as e:
                if retries >= max_retries:
                    logger.error("Max retries exceeded for rate limit error. Terminating.", module=Module.AZR)
                    logger.debug(str(e), module=Module.AZR)
                    raise
            self.__wait_for_retry()
            retries += 1


azure_open_ai_adapter: AzureOpenAIAdapter = AzureOpenAIAdapter()
