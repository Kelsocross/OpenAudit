import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any

class VisualizationManager:
    """Create interactive visualizations for audit results"""

    def __init__(self):
        # MAG - H&B color scheme
        self.colors = {
            'primary_blue': '#1F497D',
            'primary_orange': '#7EA1C4',
            'light_blue': '#4E75A0',
            'light_orange': '#B3C9DC',
            'gray': '#8E8E93',
            'light_gray': '#F2F2F7',
            'white': '#FFFFFF'
        }

        self.color_palette = [
            self.colors['primary_orange'],
            self.colors['primary_blue'],
            self.colors['light_blue'],
            self.colors['light_orange'],
            self.colors['gray']
        ]

    def create_error_distribution_chart(self, findings_df: pd.DataFrame) -> go.Figure:
        """Create pie chart showing distribution of error types"""
        if findings_df.empty:
            return self._create_empty_chart("No errors found")

        error_counts = findings_df['Error Type'].value_counts()

        # Create custom color mapping for specific error types
        error_type_colors = {
            'Late Delivery': self.colors['primary_orange'],
            'DIM Weight Overcharge': self.colors['primary_blue'],
            'Duplicate Tracking': self.colors['light_blue'],  # Changed to light blue
            'Incorrect Zone': self.colors['light_orange'],
            'Address Type Mismatch': self.colors['gray'],
            'Unnecessary Surcharge': '#9B9B9B',
            'Disputable Surcharge': '#C7C7CC',
            'Service Type Mismatch': '#D1D1D6'
        }

        # Assign colors based on error type, use default palette for unknown types
        chart_colors = []
        for idx, error_type in enumerate(error_counts.index):
            if error_type in error_type_colors:
                chart_colors.append(error_type_colors[error_type])
            else:
                # Use default palette for any unlisted error types
                chart_colors.append(self.color_palette[idx % len(self.color_palette)])

        fig = go.Figure(data=[
            go.Pie(
                labels=error_counts.index,
                values=error_counts.values,
                hole=0.4,
                marker_colors=chart_colors,
                textinfo='label+percent',
                textposition='outside',
                hovertemplate='<b>%{label}</b><br>' +
                             'Count: %{value}<br>' +
                             'Percentage: %{percent}<br>' +
                             '<extra></extra>'
            )
        ])

        fig.update_layout(
            title={
                'text': 'Distribution of Error Types',
                'x': 0.0,
                'y': 0.95,  # Position title higher to prevent overlap
                'xanchor': 'left',
                'yanchor': 'top',
                'font': {'size': 16, 'color': self.colors['primary_blue']}
            },
            font={'size': 12},
            showlegend=True,
            legend=dict(
                orientation="v",
                yanchor="middle",
                y=0.5,
                xanchor="left",
                x=1.02
            ),
            height=400,
            margin=dict(l=20, r=120, t=80, b=20)  # Increased top margin from 50 to 80
        )

        return fig

    def create_savings_by_category_chart(self, findings_df: pd.DataFrame) -> go.Figure:
        """Create bar chart showing savings by error category"""
        if findings_df.empty:
            return self._create_empty_chart("No savings data available")

        savings_by_category = findings_df.groupby('Error Type')['Refund Estimate'].sum().sort_values(ascending=True)

        fig = go.Figure(data=[
            go.Bar(
                x=savings_by_category.values,
                y=savings_by_category.index,
                orientation='h',
                marker_color=self.colors['primary_orange'],
                text=[f'${x:,.0f}' for x in savings_by_category.values],
                textposition='outside',
                hovertemplate='<b>%{y}</b><br>' +
                             'Savings: $%{x:,.2f}<br>' +
                             '<extra></extra>'
            )
        ])

        fig.update_layout(
            title={
                'text': 'Potential Savings by Error Category',
                'x': 0.0,
                'font': {'size': 16, 'color': self.colors['primary_blue']}
            },
            xaxis_title='Potential Savings ($)',
            yaxis_title='Error Category',
            font={'size': 12},
            height=400,
            margin=dict(l=150, r=50, t=50, b=50)
        )

        return fig

    def create_timeline_chart(self, findings_df: pd.DataFrame) -> go.Figure:
        """Create timeline chart showing overcharges over time"""
        if findings_df.empty:
            return self._create_empty_chart("No timeline data available")

        # Convert Date column to datetime
        findings_df = findings_df.copy()
        findings_df['Date'] = pd.to_datetime(findings_df['Date'])

        # Group by week and sum refund estimates
        findings_df['Week'] = findings_df['Date'].dt.to_period('W').dt.start_time
        weekly_savings = findings_df.groupby('Week')['Refund Estimate'].sum().reset_index()

        # Also get error counts by week
        weekly_counts = findings_df.groupby('Week').size().reset_index(name='Error_Count')

        # Merge data
        weekly_data = pd.merge(weekly_savings, weekly_counts, on='Week')

        # Create subplot with secondary y-axis
        fig = make_subplots(
            specs=[[{"secondary_y": True}]]
        )

        # Add savings bar chart
        fig.add_trace(
            go.Bar(
                x=weekly_data['Week'],
                y=weekly_data['Refund Estimate'],
                name='Potential Savings',
                marker_color=self.colors['primary_orange'],
                hovertemplate='Week: %{x}<br>' +
                             'Savings: $%{y:,.2f}<br>' +
                             '<extra></extra>'
            ),
            secondary_y=False
        )

        # Add error count line
        fig.add_trace(
            go.Scatter(
                x=weekly_data['Week'],
                y=weekly_data['Error_Count'],
                mode='lines+markers',
                name='Error Count',
                line=dict(color=self.colors['primary_blue'], width=3),
                marker=dict(size=8),
                hovertemplate='Week: %{x}<br>' +
                             'Errors: %{y}<br>' +
                             '<extra></extra>'
            ),
            secondary_y=True
        )

        # Update layout
        fig.update_layout(
            title=dict(
                text='<b>Weekly Overcharges and Error Frequency</b>',
                x=0.0,
                y=0.95,
                xanchor='left',
                font=dict(size=16, color=self.colors['primary_blue'])
            ),
            legend=dict(
                orientation='h',
                yanchor='top',
                y=1.5,
                xanchor='left',
                x=0.5,
                font=dict(size=11)
            ),
            xaxis=dict(
                title='Week',
                tickformat='%b %d',
                showgrid=False
            ),
            yaxis=dict(
                title='Potential Savings ($)',
                showgrid=True,
                gridcolor='lightgrey',
                range=[0, weekly_data['Refund Estimate'].max() * 1.1],
                dtick=5000
            ),
            yaxis2=dict(
                title='Number of Errors',
                overlaying='y',
                side='right',
                showgrid=False,
                range=[0, weekly_data['Error_Count'].max() * 1.1]
                # Removed dtick to allow automatic gradual scaling
            ),
            margin=dict(l=60, r=100, t=5, b=50),
            height=450,
            hovermode='x unified',
            font=dict(size=12)
        )

        return fig

    def create_ltl_trends_chart(self, findings_df: pd.DataFrame, time_period: str = 'weekly') -> go.Figure:
        """
        Create trend chart for LTL duplicate charges over time
        
        Args:
            findings_df: DataFrame with LTL duplicate charge findings
            time_period: 'weekly' or 'monthly' grouping
        
        Returns:
            Plotly figure with bars for duplicate invoice counts and line for refund amounts
        """
        if findings_df.empty or 'Date' not in findings_df.columns:
            return self._create_empty_chart("No date information available for trend analysis")
        
        # Convert Date column to datetime
        findings_df = findings_df.copy()
        findings_df['Date'] = pd.to_datetime(findings_df['Date'])
        
        # Group by time period
        if time_period == 'monthly':
            findings_df['Period'] = findings_df['Date'].dt.to_period('M').dt.start_time
            period_label = 'Month'
            date_format = '%b %Y'
        else:  # weekly
            findings_df['Period'] = findings_df['Date'].dt.to_period('W').dt.start_time
            period_label = 'Week'
            date_format = '%b %d'
        
        # Group by period and sum refund amounts
        period_refunds = findings_df.groupby('Period')['Potential Refund'].sum().reset_index()
        
        # Count unique invoices with duplicates per period
        period_invoice_counts = findings_df.groupby('Period')['Invoice Number'].nunique().reset_index(name='Invoice_Count')
        
        # Merge data
        period_data = pd.merge(period_refunds, period_invoice_counts, on='Period')
        
        # Create subplot with secondary y-axis
        fig = make_subplots(
            specs=[[{"secondary_y": True}]]
        )
        
        # Add invoice count bar chart (primary)
        fig.add_trace(
            go.Bar(
                x=period_data['Period'],
                y=period_data['Invoice_Count'],
                name='Duplicate Invoices',
                marker_color=self.colors['primary_orange'],
                hovertemplate=f'{period_label}: %{{x}}<br>' +
                             'Invoices: %{y}<br>' +
                             '<extra></extra>'
            ),
            secondary_y=False
        )
        
        # Add refund amount line (secondary)
        fig.add_trace(
            go.Scatter(
                x=period_data['Period'],
                y=period_data['Potential Refund'],
                mode='lines+markers',
                name='Potential Refund',
                line=dict(color=self.colors['primary_blue'], width=3),
                marker=dict(size=8),
                hovertemplate=f'{period_label}: %{{x}}<br>' +
                             'Refund: $%{y:,.2f}<br>' +
                             '<extra></extra>'
            ),
            secondary_y=True
        )
        
        # Update layout
        fig.update_layout(
            title=dict(
                text=f'<b>{period_label}ly Duplicate Charges Trend</b>',
                x=0.0,
                y=0.95,
                xanchor='left',
                font=dict(size=16, color=self.colors['primary_blue'])
            ),
            legend=dict(
                orientation='h',
                yanchor='top',
                y=1.5,
                xanchor='left',
                x=0.5,
                font=dict(size=11)
            ),
            xaxis=dict(
                title=period_label,
                tickformat=date_format,
                showgrid=False
            ),
            yaxis=dict(
                title='Number of Invoices',
                showgrid=True,
                gridcolor='lightgrey',
                range=[0, period_data['Invoice_Count'].max() * 1.1] if not period_data.empty else [0, 10],
            ),
            yaxis2=dict(
                title='Potential Refund ($)',
                overlaying='y',
                side='right',
                showgrid=False,
                range=[0, period_data['Potential Refund'].max() * 1.1] if not period_data.empty else [0, 100],
            ),
            margin=dict(l=60, r=60, t=5, b=50),
            height=450,
            hovermode='x unified',
            font=dict(size=12)
        )
        
        return fig

    def create_carrier_comparison_chart(self, findings_df: pd.DataFrame) -> go.Figure:
        """Create chart comparing errors and savings by carrier"""
        if findings_df.empty or 'Carrier' not in findings_df.columns:
            return self._create_empty_chart("No carrier data available")

        carrier_summary = findings_df.groupby('Carrier').agg({
            'Refund Estimate': 'sum',
            'Tracking Number': 'count'
        }).reset_index()

        carrier_summary.columns = ['Carrier', 'Total_Savings', 'Error_Count']

        fig = go.Figure()

        # Add savings bars
        fig.add_trace(go.Bar(
            x=carrier_summary['Carrier'],
            y=carrier_summary['Total_Savings'],
            name='Potential Savings',
            marker_color=self.colors['primary_orange'],
            yaxis='y',
            offsetgroup=1,
            hovertemplate='<b>%{x}</b><br>' +
                         'Savings: $%{y:,.2f}<br>' +
                         '<extra></extra>'
        ))

        # Add error count bars
        fig.add_trace(go.Bar(
            x=carrier_summary['Carrier'],
            y=carrier_summary['Error_Count'],
            name='Error Count',
            marker_color=self.colors['primary_blue'],
            yaxis='y2',
            offsetgroup=2,
            hovertemplate='<b>%{x}</b><br>' +
                         'Errors: %{y}<br>' +
                         '<extra></extra>'
        ))

        # Update layout with secondary y-axis
        fig.update_layout(
            title={
                'text': 'Carrier Comparison: Errors and Savings',
                'x': 0.5,
                'font': {'size': 16, 'color': self.colors['primary_blue']}
            },
            xaxis_title='Carrier',
            yaxis=dict(
                title='Potential Savings ($)',
                side='left'
            ),
            yaxis2=dict(
                title='Number of Errors',
                side='right',
                overlaying='y'
            ),
            font={'size': 12},
            height=400,
            barmode='group'
        )

        return fig

    def create_service_type_analysis(self, findings_df: pd.DataFrame) -> go.Figure:
        """Create analysis of errors by service type"""
        if findings_df.empty or 'Service Type' not in findings_df.columns:
            return self._create_empty_chart("No service type data available")

        service_analysis = findings_df.groupby(['Service Type', 'Error Type']).agg({
            'Refund Estimate': 'sum'
        }).reset_index()

        fig = px.sunburst(
            service_analysis,
            path=['Service Type', 'Error Type'],
            values='Refund Estimate',
            color='Refund Estimate',
            color_continuous_scale=['#F0F0F0', self.colors['primary_orange']],
            title='Service Type and Error Analysis'
        )

        fig.update_layout(
            title={
                'text': 'Error Distribution by Service Type',
                'x': 0.5,
                'font': {'size': 16, 'color': self.colors['primary_blue']}
            },
            font={'size': 12},
            height=500
        )

        return fig

    def create_monthly_trend_chart(self, findings_df: pd.DataFrame) -> go.Figure:
        """Create monthly trend analysis"""
        if findings_df.empty:
            return self._create_empty_chart("No data available for trends")

        findings_df = findings_df.copy()
        findings_df['Date'] = pd.to_datetime(findings_df['Date'])
        findings_df['Month'] = findings_df['Date'].dt.to_period('M').dt.start_time

        monthly_data = findings_df.groupby(['Month', 'Error Type']).agg({
            'Refund Estimate': 'sum'
        }).reset_index()

        fig = px.line(
            monthly_data,
            x='Month',
            y='Refund Estimate',
            color='Error Type',
            title='Monthly Trend by Error Type',
            color_discrete_sequence=self.color_palette
        )

        fig.update_layout(
            title={
                'text': 'Monthly Error Trends',
                'x': 0.5,
                'font': {'size': 16, 'color': self.colors['primary_blue']}
            },
            xaxis_title='Month',
            yaxis_title='Potential Savings ($)',
            font={'size': 12},
            height=400,
            hovermode='x unified'
        )

        return fig

    def _create_empty_chart(self, message: str) -> go.Figure:
        """Create empty chart with message"""
        fig = go.Figure()

        fig.add_annotation(
            text=message,
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            xanchor="center",
            yanchor="middle",
            font=dict(size=16, color=self.colors['gray']),
            showarrow=False
        )

        fig.update_layout(
            height=400,
            showlegend=False,
            xaxis={'visible': False},
            yaxis={'visible': False},
            margin=dict(l=50, r=50, t=50, b=50)
        )

        return fig
