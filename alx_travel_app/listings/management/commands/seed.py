# listings/management/commands/seed.py
import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from listings.models import Listing, Booking, Review, ListingImage


class Command(BaseCommand):
    help = 'Populate the database with sample listings, bookings, and reviews'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear all existing data before seeding',
        )
        parser.add_argument(
            '--users',
            type=int,
            default=5,
            help='Number of sample users to create',
        )
        parser.add_argument(
            '--listings',
            type=int,
            default=20,
            help='Number of sample listings to create',
        )

    def handle(self, *args, **options):
        clear_data = options['clear']
        num_users = options['users']
        num_listings = options['listings']

        if clear_data:
            self.stdout.write('Clearing existing data...')
            ListingImage.objects.all().delete()
            Review.objects.all().delete()
            Booking.objects.all().delete()
            Listing.objects.all().delete()
            User.objects.filter(is_superuser=False).delete()
            self.stdout.write(
                self.style.SUCCESS('Existing data cleared successfully!')
            )

        self.stdout.write('Starting database seeding...')

        # Create sample users
        users = self.create_sample_users(num_users)
        
        # Create sample listings
        listings = self.create_sample_listings(num_listings, users)
        
        # Create sample bookings
        bookings = self.create_sample_bookings(listings, users)
        
        # Create sample reviews
        self.create_sample_reviews(bookings)
        
        # Create sample images
        self.create_sample_images(listings)

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully seeded database with:\n'
                f'- {len(users)} users\n'
                f'- {len(listings)} listings\n'
                f'- {len(bookings)} bookings\n'
                f'- {Review.objects.count()} reviews\n'
                f'- {ListingImage.objects.count()} images'
            )
        )

    def create_sample_users(self, num_users):
        """Create sample users"""
        self.stdout.write('Creating sample users...')
        
        users = []
        
        # Create a default admin user if it doesn't exist
        if not User.objects.filter(username='admin').exists():
            admin_user = User.objects.create_superuser(
                username='admin',
                email='admin@alxtravel.com',
                password='admin123'
            )
            users.append(admin_user)
            self.stdout.write(
                self.style.SUCCESS(f'Created admin user: {admin_user.username}')
            )

        # Create regular users
        first_names = ['John', 'Jane', 'Mike', 'Sarah', 'David', 'Lisa', 'Chris', 'Emily', 'Alex', 'Maria']
        last_names = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis', 'Rodriguez', 'Martinez']
        
        for i in range(num_users):
            first_name = random.choice(first_names)
            last_name = random.choice(last_names)
            username = f"{first_name.lower()}{last_name.lower()}{i}"
            email = f"{username}@example.com"
            
            user = User.objects.create_user(
                username=username,
                email=email,
                password='password123',
                first_name=first_name,
                last_name=last_name
            )
            users.append(user)
            self.stdout.write(f'Created user: {user.username}')

        return users

    def create_sample_listings(self, num_listings, users):
        """Create sample listings"""
        self.stdout.write('Creating sample listings...')
        
        cities = [
            ('New York', 'NY', 'USA'),
            ('Los Angeles', 'CA', 'USA'),
            ('Chicago', 'IL', 'USA'),
            ('Miami', 'FL', 'USA'),
            ('Seattle', 'WA', 'USA'),
            ('Austin', 'TX', 'USA'),
            ('Boston', 'MA', 'USA'),
            ('San Francisco', 'CA', 'USA'),
            ('London', 'London', 'UK'),
            ('Paris', 'Île-de-France', 'France'),
            ('Tokyo', 'Tokyo', 'Japan'),
            ('Sydney', 'NSW', 'Australia'),
        ]
        
        listing_titles = [
            "Cozy {type} in {city}",
            "Beautiful {type} with Amazing Views",
            "Modern {type} in City Center",
            "Spacious {type} Near Attractions",
            "Luxury {type} with Premium Amenities",
            "Charming {type} in Quiet Neighborhood",
            "Stylish {type} with Garden",
            "Bright {type} with Balcony",
            "Elegant {type} for Families",
            "Contemporary {type} with Parking",
        ]
        
        descriptions = [
            "This beautiful {type} offers a perfect blend of comfort and style. Located in the heart of {city}, you'll have easy access to all major attractions.",
            "Experience luxury living in this stunning {type}. Featuring modern amenities and thoughtful design, this is the perfect getaway.",
            "A cozy retreat in {city} that feels like home. This {type} is perfect for couples, solo adventurers, and business travelers.",
            "Spacious and well-appointed {type} in a prime location. Enjoy the best of {city} with all the comforts of home.",
            "Modern {type} with high-end finishes and spectacular views. Perfect for those who appreciate quality and design.",
        ]
        
        listings = []
        
        for i in range(num_listings):
            city, state, country = random.choice(cities)
            property_type = random.choice(['apartment', 'house', 'condo', 'villa', 'studio', 'cabin'])
            host = random.choice(users)
            
            title_template = random.choice(listing_titles)
            title = title_template.format(type=property_type.title(), city=city)
            
            description_template = random.choice(descriptions)
            description = description_template.format(type=property_type, city=city)
            
            # Generate realistic pricing based on property type and location
            base_prices = {
                'apartment': (80, 200),
                'house': (120, 350),
                'condo': (90, 250),
                'villa': (200, 500),
                'studio': (60, 150),
                'cabin': (70, 180),
            }
            min_price, max_price = base_prices[property_type]
            base_price = random.randint(min_price, max_price)
            
            listing = Listing.objects.create(
                title=title,
                description=description,
                property_type=property_type,
                address=f"{random.randint(100, 999)} {random.choice(['Main', 'Oak', 'Maple', 'Pine', 'Cedar'])} St",
                city=city,
                state=state,
                country=country,
                zip_code=f"{random.randint(10000, 99999)}",
                latitude=random.uniform(-90, 90),
                longitude=random.uniform(-180, 180),
                max_guests=random.randint(2, 8),
                bedrooms=random.randint(1, 4),
                beds=random.randint(1, 6),
                bathrooms=random.randint(1, 3),
                wifi=random.choice([True, False]),
                kitchen=random.choice([True, False]),
                parking=random.choice([True, False]),
                pool=random.choice([True, False]),
                air_conditioning=random.choice([True, False]),
                heating=random.choice([True, False]),
                tv=random.choice([True, False]),
                base_price=base_price,
                cleaning_fee=random.choice([0, 25, 50, 75]),
                security_deposit=random.choice([0, 100, 200, 300]),
                host=host,
                status='active',
                minimum_stay=random.randint(1, 3),
                maximum_stay=random.randint(14, 60),
            )
            listings.append(listing)
            self.stdout.write(f'Created listing: {listing.title}')

        return listings

    def create_sample_bookings(self, listings, users):
        """Create sample bookings"""
        self.stdout.write('Creating sample bookings...')
        
        bookings = []
        
        for listing in listings:
            # Create 1-3 bookings per listing
            num_bookings = random.randint(1, 3)
            
            for _ in range(num_bookings):
                guest = random.choice([u for u in users if u != listing.host])
                
                # Generate random dates in the past and future
                days_ago = random.randint(1, 180)
                check_in = timezone.now().date() - timedelta(days=days_ago)
                duration = random.randint(2, 14)
                check_out = check_in + timedelta(days=duration)
                
                # Determine booking status based on dates
                today = timezone.now().date()
                if check_out < today:
                    status = 'completed'
                elif check_in <= today <= check_out:
                    status = 'active'
                else:
                    status = random.choice(['pending', 'confirmed'])
                
                number_of_guests = random.randint(1, listing.max_guests)
                total_price = duration * listing.base_price + listing.cleaning_fee
                
                booking = Booking.objects.create(
                    listing=listing,
                    guest=guest,
                    check_in=check_in,
                    check_out=check_out,
                    number_of_guests=number_of_guests,
                    guest_special_requests=random.choice([
                        '', 
                        'Early check-in if possible',
                        'Traveling with a small child',
                        'Business trip',
                        'Celebrating anniversary',
                        'Quiet location preferred'
                    ]),
                    total_price=total_price,
                    security_deposit_held=listing.security_deposit,
                    status=status,
                    payment_status=random.choice(['pending', 'completed']),
                )
                
                # Set timestamps based on status
                if status in ['confirmed', 'active', 'completed']:
                    booking.confirmed_at = check_in - timedelta(days=random.randint(1, 7))
                    booking.save()
                
                bookings.append(booking)
                self.stdout.write(f'Created booking for {listing.title}')

        return bookings

    def create_sample_reviews(self, bookings):
        """Create sample reviews for completed bookings"""
        self.stdout.write('Creating sample reviews...')
        
        review_titles = [
            "Great stay!",
            "Wonderful experience",
            "Perfect location",
            "Comfortable and clean",
            "Would stay again",
            "Amazing host",
            "Beautiful property",
            "Highly recommended",
            "Lovely place",
            "Excellent value",
        ]
        
        review_comments = [
            "We had a wonderful time at this property. The location was perfect and the host was very responsive.",
            "Clean, comfortable, and exactly as described. Would definitely recommend to others.",
            "Great value for the price. The amenities were exactly what we needed for our stay.",
            "The host was very accommodating and the property was beautiful. We'll be back!",
            "Perfect location for exploring the city. The property had everything we needed.",
            "Very comfortable stay with all the necessary amenities. The host was very helpful.",
            "Beautiful property with great attention to detail. We thoroughly enjoyed our stay.",
            "The photos don't do this place justice! It was even better in person.",
            "Excellent communication from the host and a very smooth check-in process.",
            "We loved our stay here. The property was clean, comfortable, and well-located.",
        ]
        
        for booking in bookings:
            # Only create reviews for completed bookings (50% chance)
            if booking.status == 'completed' and random.choice([True, False]):
                rating = random.randint(4, 5)  # Mostly positive reviews
                
                review = Review.objects.create(
                    listing=booking.listing,
                    booking=booking,
                    author=booking.guest,
                    rating=rating,
                    title=random.choice(review_titles),
                    comment=random.choice(review_comments),
                    is_verified=True,
                    is_public=True,
                )
                
                # Add host response for some reviews (30% chance)
                if random.random() < 0.3:
                    host_responses = [
                        "Thank you for your kind words! We're so glad you enjoyed your stay.",
                        "We appreciate your feedback and would love to host you again in the future!",
                        "Thank you for being wonderful guests! We're happy you had a great experience.",
                        "We're delighted you enjoyed your stay. Hope to see you again soon!",
                    ]
                    review.host_response = random.choice(host_responses)
                    review.host_response_at = review.created_at + timedelta(hours=random.randint(1, 24))
                    review.save()
                
                self.stdout.write(f'Created review for {booking.listing.title}')

    def create_sample_images(self, listings):
        """Create placeholder image references (in a real app, these would be actual image files)"""
        self.stdout.write('Creating sample image references...')
        
        image_descriptions = [
            "Living room",
            "Bedroom",
            "Kitchen",
            "Bathroom",
            "Exterior",
            "Balcony view",
            "Swimming pool",
            "Garden",
            "Dining area",
            "City view",
        ]
        
        for listing in listings:
            # Create 3-6 images per listing
            num_images = random.randint(3, 6)
            
            for i in range(num_images):
                is_primary = (i == 0)  # First image is primary
                
                ListingImage.objects.create(
                    listing=listing,
                    image=f'listing_images/sample_{random.randint(1, 10)}.jpg',  # Placeholder
                    caption=random.choice(image_descriptions),
                    is_primary=is_primary,
                    order=i,
                )
            
            self.stdout.write(f'Created {num_images} images for {listing.title}')