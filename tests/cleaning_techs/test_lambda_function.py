import unittest
from unittest.mock import patch
from cleaning_techs.lambda_function import remove_techs_exact, map_techs

class TestCleaningTechs(unittest.TestCase):
    
    def test_remove_techs_exact(self):
        "Testing the remove_techs_exact function"
        
        # Define input and expected output
        pattern_example = [
            '\\bskills\\b',
            '\\banalyst\\b',
            '\\bdocumentation\\b',
            '\\bprototyping tools\\b'
        ]
                           
        input_example = ['excel skills', 'powerbi analyst', 'documentation guide', 'prototype', 'test']
        expected_result = ['prototype', 'test']
        
        # Call the function and check the output
        result = remove_techs_exact(input_example, pattern_example)
        self.assertEqual(result, expected_result)
    
    def test_map_techs(self):
        "Testing the map_techs function"
        
        # Define input and expected output
        pattern_example = {
            r'\b(aws|amazon)\b': 'aws',
            r'\b(ai|artificial intelligence|contextual ai)\b': 'ai',
            r'\b(google|gcp)\b': 'google',
            r'\b(power bi|powerbi)\b': 'powerbi',
            r'\b(excel)\b':'excel',
            r'\b(microsoft word|ms word|ms office)\b':'microsoft office',
        }
        input_example = ['ai tech', 'gcp', 'rgoogleey', 'laws', 'aws lambda', 
                         'ms excel', 'excellant', '"ai"', '["ai"]']
        
        expected_result = ['ai', 'google', 'rgoogleey', 'laws', 'aws', 
                           'excel', 'excellant', 'ai', 'ai']
        
        # Call the function and check the output
        result = map_techs(input_example, pattern_example)
        self.assertEqual(result, expected_result)
        
if __name__ == '__main__':
    unittest.main()
