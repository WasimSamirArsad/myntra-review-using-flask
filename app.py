from flask import Flask, render_template, request, redirect, session
import pandas as pd
import matplotlib.pyplot as plt
import base64
from io import BytesIO
from src.cloud_io import MongoIO
from src.constants import SESSION_PRODUCT_KEY
from src.scrapper.scrape import ScrapeReviews
import io


app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Flask sessions require a secret key

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Get form input
        product = request.form.get('product')
        no_of_products = int(request.form.get('no_of_products'))

        # Store product name in session
        session[SESSION_PRODUCT_KEY] = product

        # Call the ScrapeReviews function
        scrapper = ScrapeReviews(
            product_name=product,
            no_of_products=no_of_products
        )

        # Get scraped review data
        scrapped_data = scrapper.get_review_data()

        if scrapped_data is not None:
            # Store scrapped data in the database
            mongoio = MongoIO()
            mongoio.store_reviews(product_name=product, reviews=scrapped_data)

            # Store scrapped data in the session (convert DataFrame to dict)
            session['scrapped_data'] = scrapped_data.to_dict(orient='records')

            return redirect('/analysis')  # Redirect to analysis page

    return render_template('index.html')

@app.route('/analysis', methods=['GET'])
def analysis():
    # Retrieve the data from the session
    if 'scrapped_data' in session:
        # Convert session data back to DataFrame
        data = pd.DataFrame(session['scrapped_data'])

        # Generate the plots
        plot_url = create_plot(data)
        pie_plot_url=create_pie_chart(data)

        # Convert the DataFrame to HTML to display in the template
        data_html = data.to_html(classes='data', header="true", index=False)

        return render_template('scrape_results.html', data_html=data_html, plot_url=plot_url,pie_plot_url=pie_plot_url)

    return render_template('show.html', message="No data available for analysis. Please go back to the search page.")

@app.route('/reset', methods=['GET'])
def reset():
    # Clear session data (optional: create a reset route)
    session.pop('scrapped_data', None)
    session.pop(SESSION_PRODUCT_KEY, None)
    return redirect('/')  # Redirect back to index

def create_plot(data):
    # Example: Create a bar plot of average ratings
    plt.figure(figsize=(10, 6))
    data['Rating'] = data['Rating'].astype(float)  # Ensure ratings are float
    avg_ratings = data.groupby('Product Name')['Rating'].mean()
    
    avg_ratings.plot(kind='bar', color='skyblue')
    plt.title('Average Ratings by Product')
    plt.xlabel('Product Name')
    plt.ylabel('Average Rating')
    plt.xticks(rotation=45)
    
    # Save the plot to a BytesIO object
    img = BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    plt.close()

    
    # Encode the image to base64 for HTML rendering
    plot_url = base64.b64encode(img.getvalue()).decode('utf-8')
    return f"data:image/png;base64,{plot_url}"


def create_pie_chart(data):
    # Create a pie chart using matplotlib

    plt.figure(figsize=(10, 10))
    # fig, ax = plt.subplots()
    plt.pie(data['Rating'], labels=data['Name'], autopct='%1.1f%%', startangle=90)
    plt.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
    
    # Save it to a bytes buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    
    # Encode the image to base64
    plot_url = base64.b64encode(buf.getvalue()).decode('utf8')
    
    return f"data:image/png;base64,{plot_url}"


if __name__ == '__main__':
    app.run(debug=True)
