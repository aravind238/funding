from decimal import Decimal, ROUND_CEILING, ROUND_DOWN, ROUND_FLOOR, ROUND_HALF_DOWN, ROUND_HALF_EVEN, ROUND_HALF_UP, ROUND_UP, ROUND_05UP
from .response import custom_response

# For reference https://docs.python.org/3/library/decimal.html

"""
================
rounding_option:
================
ROUND_CEILING (Round towards Infinity),
ROUND_DOWN (Round towards zero),
ROUND_FLOOR (Round towards -Infinity),
ROUND_HALF_DOWN (Round to nearest with ties going towards zero),
ROUND_HALF_EVEN (Round to nearest with ties going to nearest even integer),
ROUND_HALF_UP (Round to nearest with ties going away from zero), 
ROUND_UP (Round away from zero),
ROUND_05UP (Round away from zero if last digit after rounding towards zero would have been 0 or 5; otherwise round towards zero)

===========================================
quantize(exp, rounding=None, context=None):
===========================================
Returns a value equal to the first operand after rounding and having the exponent of the second operand.

==============
to_integral():
==============
Returns the rounded integral value.

"""

def bankers_rounding(calculation_rounding = float(0), rounding_option=ROUND_HALF_EVEN): 
    try:
        calculation_rounded = float(0)
        
        if isinstance(calculation_rounding, str):
            return custom_response({'status': 'error', 'msg': 'Only integer or decimal values are supported'}, 404)

        if isinstance(calculation_rounding, int) or len(str(calculation_rounding).split(".")) == 1:
            calculation_rounding = float(calculation_rounding)

        if (calculation_rounding > 0) and (calculation_rounding < 100) and (len(str(calculation_rounding).split(".")[1]) == 1):
            calculation_rounded = Decimal(calculation_rounding).to_integral(rounding=rounding_option) 
            calculation_rounding = Decimal(calculation_rounding)
        else:           
            calculation_rounding = Decimal(calculation_rounding)
            calculation_rounded = calculation_rounding.quantize(Decimal('1.00'), rounding=rounding_option).quantize(Decimal('0.01'))

        return {
            'original_value' : calculation_rounding,
            'bankers_rounding' : calculation_rounded
        }
    except Exception as e:
        print(str(e))
        return custom_response({'status': 'error', 'msg': str(e)}, 404)