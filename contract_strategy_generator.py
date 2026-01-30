"""
Contract Strategy Generator for OpenAudit
"""
from typing import Dict, Any, List
import json

class StrategyGenerator:
    """Generate negotiation strategies based on contract analysis"""
    
    def generate_strategy(self, contract_terms: Dict[str, Any], benchmark_comparison: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive negotiation strategy"""
        
        carrier = contract_terms.get('carrier', 'Unknown')
        current_discount = benchmark_comparison.get('current_discount', 0)
        best_discount = benchmark_comparison.get('best_discount', 0)
        discount_gap = benchmark_comparison.get('discount_gap', 0)
        
        # Generate strategy narrative
        strategy_text = self._generate_strategy_text(carrier, current_discount, best_discount, discount_gap)
        
        # Generate key recommendations
        recommendations = self._generate_recommendations(contract_terms, benchmark_comparison)
        
        return {
            'negotiation_strategy': strategy_text,
            'key_recommendations': recommendations
        }
    
    def _generate_strategy_text(self, carrier: str, current_discount: float, best_discount: float, discount_gap: float) -> str:
        """Generate strategy narrative"""
        strategy = f"""
## Negotiation Strategy for {carrier} Contract

### Current Position
Your current contract has a base discount of {current_discount}%. Industry leaders in your segment are achieving discounts up to {best_discount}%, representing a gap of {discount_gap}%.

### Recommended Approach

1. **Leverage Volume and Competition**
   - Emphasize your shipping volume and growth potential
   - Reference competitive quotes from alternative carriers
   - Highlight your reliability as a shipper

2. **Focus on High-Impact Terms**
   - Negotiate base discount percentage first
   - Address dimensional weight divisor (request 139 instead of current)
   - Renegotiate residential and delivery area surcharges

3. **Timing and Preparation**
   - Prepare 6 months of shipping data showing patterns
   - Time negotiation before contract renewal (60-90 days out)
   - Have alternative carrier quotes ready as leverage

4. **Incremental Wins**
   - If full discount target seems unrealistic, negotiate in phases
   - Secure commitment for annual reviews
   - Build in performance-based discount increases

### Key Talking Points
- "Our shipping volume has grown X% over the past year"
- "We're evaluating multiple carrier options for optimal cost efficiency"
- "Industry benchmarks show discounts in the {best_discount}% range for similar shippers"
- "We're looking for a long-term partnership with mutually beneficial terms"
"""
        return strategy
    
    def _generate_recommendations(self, contract_terms: Dict[str, Any], benchmark_comparison: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate specific recommendations"""
        recommendations = []
        
        # Discount recommendation
        discount_gap = benchmark_comparison.get('discount_gap', 0)
        if discount_gap > 0:
            recommendations.append({
                'priority': 'High',
                'category': 'Base Discount',
                'current_value': f"{benchmark_comparison.get('current_discount', 0)}%",
                'target_value': f"{benchmark_comparison.get('best_discount', 0)}%",
                'potential_savings': f"${benchmark_comparison.get('discount_gap', 0) * 1000:.2f} annually per $100k spend",
                'action': f"Request increase to {benchmark_comparison.get('average_discount', 0)}% as minimum, targeting {benchmark_comparison.get('best_discount', 0)}%"
            })
        
        # DIM divisor recommendation
        dim_gap = benchmark_comparison.get('dim_gap', 0)
        if dim_gap > 0:
            recommendations.append({
                'priority': 'High',
                'category': 'DIM Divisor',
                'current_value': str(benchmark_comparison.get('current_dim', 166)),
                'target_value': str(benchmark_comparison.get('best_dim', 139)),
                'potential_savings': 'Up to 15% on lightweight packages',
                'action': f"Negotiate DIM divisor reduction from {benchmark_comparison.get('current_dim', 166)} to {benchmark_comparison.get('best_dim', 139)}"
            })
        
        # Surcharge recommendations
        recommendations.append({
            'priority': 'Medium',
            'category': 'Residential Surcharge',
            'current_value': f"${contract_terms.get('residential_surcharge', 4.95)}",
            'target_value': '$3.50 or waived',
            'potential_savings': 'Significant for B2C shippers',
            'action': 'Request residential surcharge waiver or reduction based on volume'
        })
        
        recommendations.append({
            'priority': 'Medium',
            'category': 'Fuel Surcharge',
            'current_value': f"{contract_terms.get('fuel_surcharge_pct', 12.5)}%",
            'target_value': '10-11%',
            'potential_savings': '1-2% on total freight costs',
            'action': 'Negotiate fuel surcharge cap or reduction'
        })
        
        return recommendations

def get_strategy_generator():
    """Get strategy generator instance"""
    return StrategyGenerator()
