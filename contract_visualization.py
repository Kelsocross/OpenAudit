"""
Contract Visualization for OpenAudit
"""
import plotly.graph_objects as go
from typing import Dict, Any

class ContractVisualizationManager:
    """Create visualizations for contract analysis"""
    
    def __init__(self):
        self.colors = {
            'primary_blue': '#1F497D',
            'primary_orange': '#FFA947',
            'light_blue': '#4A90E2',
            'light_orange': '#FFB366',
            'gray': '#8E8E93',
            'success': '#28a745',
            'warning': '#ffc107',
            'danger': '#dc3545'
        }
    
    def create_discount_comparison_chart(self, current: float, average: float, best: float) -> go.Figure:
        """Create discount comparison bar chart"""
        fig = go.Figure(data=[
            go.Bar(
                x=['Your Contract', 'Industry Average', 'Best-in-Class'],
                y=[current, average, best],
                marker_color=[self.colors['danger'], self.colors['warning'], self.colors['success']],
                text=[f'{current}%', f'{average}%', f'{best}%'],
                textposition='outside'
            )
        ])
        
        fig.update_layout(
            title='Discount Comparison',
            yaxis_title='Discount Percentage',
            showlegend=False,
            height=400
        )
        
        return fig
    
    def create_savings_potential_chart(self, estimated_savings: float) -> go.Figure:
        """Create savings potential gauge chart"""
        fig = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=estimated_savings,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "Annual Savings Potential"},
            delta={'reference': 0},
            gauge={
                'axis': {'range': [None, estimated_savings * 2]},
                'bar': {'color': self.colors['primary_orange']},
                'steps': [
                    {'range': [0, estimated_savings * 0.5], 'color': self.colors['light_blue']},
                    {'range': [estimated_savings * 0.5, estimated_savings * 1.5], 'color': self.colors['light_orange']}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': estimated_savings * 1.8
                }
            }
        ))
        
        fig.update_layout(height=300)
        return fig
    
    def create_health_score_gauge(self, score: float) -> go.Figure:
        """Create contract health score gauge"""
        # Determine color based on score
        if score >= 80:
            color = self.colors['success']
        elif score >= 60:
            color = self.colors['warning']
        else:
            color = self.colors['danger']
        
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=score,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "Contract Health Score"},
            gauge={
                'axis': {'range': [None, 100]},
                'bar': {'color': color},
                'steps': [
                    {'range': [0, 60], 'color': '#ffebee'},
                    {'range': [60, 80], 'color': '#fff3e0'},
                    {'range': [80, 100], 'color': '#e8f5e9'}
                ]
            }
        ))
        
        fig.update_layout(height=300)
        return fig

    def create_contract_timeline_comparison(self) -> go.Figure:
        """Create placeholder timeline comparison chart"""
        import pandas as pd
        from datetime import datetime, timedelta
        
        # Create sample timeline data
        today = datetime.now()
        dates = [today - timedelta(days=90*i) for i in range(4, 0, -1)]
        
        fig = go.Figure()
        
        # Sample data for contract health scores over time
        fig.add_trace(go.Scatter(
            x=dates,
            y=[45, 52, 68, 75],
            mode='lines+markers',
            name='Contract Health Score',
            line=dict(color=self.colors['primary_blue'], width=3),
            marker=dict(size=10)
        ))
        
        fig.update_layout(
            title='Contract Performance Over Time (Sample Data)',
            xaxis_title='Date',
            yaxis_title='Health Score',
            yaxis=dict(range=[0, 100]),
            showlegend=True,
            height=400
        )
        
        return fig

def get_visualization_manager():
    """Get visualization manager instance"""
    return ContractVisualizationManager()
