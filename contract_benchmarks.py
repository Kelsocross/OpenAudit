"""
Contract Benchmarks for OpenAudit
"""
from typing import Dict, Any, List, Tuple

class BenchmarkEngine:
    """Compare contracts against industry benchmarks"""
    
    def __init__(self):
        self.benchmarks = self._load_benchmarks()
    
    def _load_benchmarks(self) -> Dict[str, Any]:
        """Load industry benchmarks"""
        return {
            'FedEx': {
                'best_discount_pct': 65.0,
                'average_discount_pct': 35.0,
                'best_dim_divisor': 139,
                'standard_fuel_surcharge': 11.5,
                'typical_residential_surcharge': 4.75,
                'typical_delivery_area_surcharge': 3.00
            },
            'UPS': {
                'best_discount_pct': 62.0,
                'average_discount_pct': 33.0,
                'best_dim_divisor': 139,
                'standard_fuel_surcharge': 11.5,
                'typical_residential_surcharge': 4.95,
                'typical_delivery_area_surcharge': 3.25
            },
            'USPS': {
                'best_discount_pct': 40.0,
                'average_discount_pct': 20.0,
                'best_dim_divisor': 166,
                'standard_fuel_surcharge': 10.0,
                'typical_residential_surcharge': 0.0,
                'typical_delivery_area_surcharge': 0.0
            },
            'DHL': {
                'best_discount_pct': 60.0,
                'average_discount_pct': 32.0,
                'best_dim_divisor': 139,
                'standard_fuel_surcharge': 12.0,
                'typical_residential_surcharge': 5.00,
                'typical_delivery_area_surcharge': 3.50
            },
            'Other': {
                'best_discount_pct': 50.0,
                'average_discount_pct': 25.0,
                'best_dim_divisor': 166,
                'standard_fuel_surcharge': 12.0,
                'typical_residential_surcharge': 5.00,
                'typical_delivery_area_surcharge': 3.50
            }
        }
    
    def get_benchmark_for_company(self, carrier: str, annual_spend: float) -> Dict[str, Any]:
        """Get benchmark data for a specific carrier and company size"""
        benchmark = self.benchmarks.get(carrier, self.benchmarks['Other'])
        
        # Adjust benchmarks based on annual spend
        if annual_spend >= 1000000:  # $1M+ 
            # Large shippers get better benchmarks
            benchmark = benchmark.copy()
            benchmark['best_discount_pct'] = min(benchmark['best_discount_pct'] * 1.1, 75.0)
        elif annual_spend < 100000:  # Under $100k
            # Small shippers have lower benchmarks
            benchmark = benchmark.copy()
            benchmark['best_discount_pct'] = benchmark['best_discount_pct'] * 0.8
        
        return benchmark
    
    def compare_contract_to_benchmark(self, contract_terms: Dict[str, Any], benchmark: Dict[str, Any]) -> Dict[str, Any]:
        """Compare contract terms to benchmark data"""
        comparison = {}
        
        # Compare base discount
        if contract_terms.get('base_discount_pct') is not None:
            current = contract_terms['base_discount_pct']
            best = benchmark['best_discount_pct']
            avg = benchmark['average_discount_pct']
            
            if current >= best * 0.95:
                tier = 'excellent'
            elif current >= avg:
                tier = 'good'
            elif current >= avg * 0.8:
                tier = 'fair'
            else:
                tier = 'poor'
            
            comparison['base_discount_pct'] = {
                'current': current,
                'average': avg,
                'best_in_class': best,
                'performance_tier': tier,
                'gap': best - current
            }
        
        # Compare DIM divisor
        if contract_terms.get('dim_divisor') is not None:
            current = contract_terms['dim_divisor']
            best = benchmark['best_dim_divisor']
            
            if current <= best:
                tier = 'excellent'
            elif current <= best * 1.1:
                tier = 'good'
            elif current <= best * 1.2:
                tier = 'fair'
            else:
                tier = 'poor'
            
            comparison['dim_divisor'] = {
                'current': current,
                'best_in_class': best,
                'performance_tier': tier,
                'gap': current - best
            }
        
        # Compare fuel surcharge
        if contract_terms.get('fuel_surcharge_pct') is not None:
            current = contract_terms['fuel_surcharge_pct']
            standard = benchmark['standard_fuel_surcharge']
            
            if current <= standard * 0.9:
                tier = 'excellent'
            elif current <= standard:
                tier = 'good'
            elif current <= standard * 1.15:
                tier = 'fair'
            else:
                tier = 'poor'
            
            comparison['fuel_surcharge_pct'] = {
                'current': current,
                'best_in_class': standard,
                'performance_tier': tier,
                'gap': current - standard
            }
        
        # Compare residential surcharge
        if contract_terms.get('residential_surcharge') is not None:
            current = contract_terms['residential_surcharge']
            typical = benchmark['typical_residential_surcharge']
            
            if current <= typical * 0.8:
                tier = 'excellent'
            elif current <= typical:
                tier = 'good'
            elif current <= typical * 1.2:
                tier = 'fair'
            else:
                tier = 'poor'
            
            comparison['residential_surcharge'] = {
                'current': current,
                'best_in_class': typical,
                'performance_tier': tier,
                'gap': current - typical
            }
        
        # Compare delivery area surcharge
        if contract_terms.get('delivery_area_surcharge') is not None:
            current = contract_terms['delivery_area_surcharge']
            typical = benchmark['typical_delivery_area_surcharge']
            
            if current <= typical * 0.8:
                tier = 'excellent'
            elif current <= typical:
                tier = 'good'
            elif current <= typical * 1.2:
                tier = 'fair'
            else:
                tier = 'poor'
            
            comparison['delivery_area_surcharge'] = {
                'current': current,
                'best_in_class': typical,
                'performance_tier': tier,
                'gap': current - typical
            }
        
        return comparison
    
    def calculate_contract_health_score(self, comparison_results: Dict[str, Any]) -> Tuple[str, float]:
        """Calculate overall contract health score"""
        if not comparison_results:
            return 'F', 0.0
        
        tier_scores = {'excellent': 100, 'good': 75, 'fair': 50, 'poor': 25}
        total_score = 0
        count = 0
        
        for term, data in comparison_results.items():
            tier = data.get('performance_tier', 'poor')
            total_score += tier_scores.get(tier, 25)
            count += 1
        
        health_score_numeric = total_score / count if count > 0 else 0
        
        # Convert to letter grade
        if health_score_numeric >= 90:
            health_score = 'A'
        elif health_score_numeric >= 80:
            health_score = 'B'
        elif health_score_numeric >= 70:
            health_score = 'C'
        elif health_score_numeric >= 60:
            health_score = 'D'
        else:
            health_score = 'F'
        
        return health_score, health_score_numeric
    
    def estimate_annual_savings_potential(self, comparison_results: Dict[str, Any], annual_spend: float) -> Dict[str, Any]:
        """Estimate annual savings potential"""
        total_savings = 0
        savings_breakdown = {}
        
        # Calculate savings from discount improvement
        if 'base_discount_pct' in comparison_results:
            discount_data = comparison_results['base_discount_pct']
            gap = discount_data.get('gap', 0)
            if gap > 0:
                savings = (gap / 100) * annual_spend
                total_savings += savings
                savings_breakdown['discount_improvement'] = savings
        
        # Estimate savings from DIM divisor improvement (roughly 10-15% of shipments affected)
        if 'dim_divisor' in comparison_results:
            dim_data = comparison_results['dim_divisor']
            if dim_data.get('gap', 0) > 0:
                # Estimate 12% of spend affected by DIM weight
                dim_affected_spend = annual_spend * 0.12
                # Estimate 15% savings on those shipments
                savings = dim_affected_spend * 0.15
                total_savings += savings
                savings_breakdown['dim_divisor_improvement'] = savings
        
        # Calculate fuel surcharge savings
        if 'fuel_surcharge_pct' in comparison_results:
            fuel_data = comparison_results['fuel_surcharge_pct']
            gap = fuel_data.get('gap', 0)
            if gap > 0:
                # Fuel surcharge applies to all shipments
                base_freight = annual_spend * 0.7  # Estimate 70% is base freight
                savings = (gap / 100) * base_freight
                total_savings += savings
                savings_breakdown['fuel_surcharge_reduction'] = savings
        
        savings_percentage = (total_savings / annual_spend * 100) if annual_spend > 0 else 0
        
        return {
            'total_annual_savings': total_savings,
            'savings_percentage': savings_percentage,
            'breakdown': savings_breakdown
        }
    
    def generate_negotiation_recommendations(self, comparison_results: Dict[str, Any], benchmark: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate specific negotiation recommendations"""
        recommendations = []
        
        # Discount recommendation
        if 'base_discount_pct' in comparison_results:
            data = comparison_results['base_discount_pct']
            if data['performance_tier'] in ['poor', 'fair']:
                priority = 'high' if data['performance_tier'] == 'poor' else 'medium'
                recommendations.append({
                    'priority': priority,
                    'category': 'Base Discount',
                    'current': f"{data['current']:.1f}%",
                    'target': f"{data['best_in_class']:.1f}%",
                    'estimated_savings': f"${data['gap'] * 1000:.0f} per $100k spend",
                    'talking_point': f"Industry leaders achieve {data['best_in_class']:.1f}% discounts. Our volume justifies a {data['average']:.1f}% minimum.",
                    'justification': 'Discount improvement directly reduces freight costs across all shipments'
                })
        
        # DIM divisor recommendation
        if 'dim_divisor' in comparison_results:
            data = comparison_results['dim_divisor']
            if data['performance_tier'] in ['poor', 'fair']:
                priority = 'high' if data['performance_tier'] == 'poor' else 'medium'
                recommendations.append({
                    'priority': priority,
                    'category': 'DIM Divisor',
                    'current': str(int(data['current'])),
                    'target': str(int(data['best_in_class'])),
                    'estimated_savings': 'Up to 15% on lightweight packages',
                    'talking_point': f"Request DIM divisor of {int(data['best_in_class'])} to align with industry standards.",
                    'justification': 'Lower DIM divisor reduces costs for lightweight, bulky items'
                })
        
        # Fuel surcharge recommendation
        if 'fuel_surcharge_pct' in comparison_results:
            data = comparison_results['fuel_surcharge_pct']
            if data['performance_tier'] in ['poor', 'fair']:
                recommendations.append({
                    'priority': 'medium',
                    'category': 'Fuel Surcharge',
                    'current': f"{data['current']:.1f}%",
                    'target': f"{data['best_in_class']:.1f}%",
                    'estimated_savings': '1-2% reduction in total costs',
                    'talking_point': f"Negotiate fuel surcharge cap at {data['best_in_class']:.1f}%",
                    'justification': 'Fuel surcharges significantly impact total shipping costs'
                })
        
        # Residential surcharge
        if 'residential_surcharge' in comparison_results:
            data = comparison_results['residential_surcharge']
            if data['performance_tier'] in ['poor', 'fair']:
                recommendations.append({
                    'priority': 'medium',
                    'category': 'Residential Surcharge',
                    'current': f"${data['current']:.2f}",
                    'target': f"${data['best_in_class']:.2f}",
                    'estimated_savings': 'Significant for B2C shippers',
                    'talking_point': 'Request residential surcharge waiver or reduction based on volume',
                    'justification': 'High residential delivery volume warrants preferential pricing'
                })
        
        return recommendations

def get_benchmark_engine():
    """Get benchmark engine instance"""
    return BenchmarkEngine()
