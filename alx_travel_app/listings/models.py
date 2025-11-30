# listings/models.py
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone


class Listing(models.Model):
    PROPERTY_TYPES = [
        ('apartment', 'Apartment'),
        ('house', 'House'),
        ('villa', 'Villa'),
        ('condo', 'Condo'),
        ('cabin', 'Cabin'),
        ('studio', 'Studio'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('suspended', 'Suspended'),
    ]

    # Basic Information
    title = models.CharField(max_length=200)
    description = models.TextField()
    property_type = models.CharField(max_length=20, choices=PROPERTY_TYPES)
    
    # Location
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    zip_code = models.CharField(max_length=20)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    # Property Details
    max_guests = models.PositiveIntegerField()
    bedrooms = models.PositiveIntegerField()
    beds = models.PositiveIntegerField()
    bathrooms = models.PositiveIntegerField()
    
    # Amenities
    wifi = models.BooleanField(default=False)
    kitchen = models.BooleanField(default=False)
    parking = models.BooleanField(default=False)
    pool = models.BooleanField(default=False)
    air_conditioning = models.BooleanField(default=False)
    heating = models.BooleanField(default=False)
    tv = models.BooleanField(default=False)
    
    # Pricing
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    cleaning_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    security_deposit = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Host and Status
    host = models.ForeignKey(User, on_delete=models.CASCADE, related_name='listings')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Rules and Policies
    check_in_time = models.TimeField(default='15:00')
    check_out_time = models.TimeField(default='11:00')
    minimum_stay = models.PositiveIntegerField(default=1)
    maximum_stay = models.PositiveIntegerField(default=30)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'property_type']),
            models.Index(fields=['city', 'country']),
            models.Index(fields=['host']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.city}, {self.country}"
    
    def is_available(self, check_in, check_out):
        """Check if listing is available for given dates"""
        overlapping_bookings = self.bookings.filter(
            models.Q(check_in__lt=check_out) & models.Q(check_out__gt=check_in),
            status__in=['confirmed', 'active']
        )
        return not overlapping_bookings.exists()
    
    @property
    def average_rating(self):
        """Calculate average rating from reviews"""
        reviews = self.reviews.all()
        if reviews:
            return sum(review.rating for review in reviews) / len(reviews)
        return 0
    
    @property
    def review_count(self):
        """Get total number of reviews"""
        return self.reviews.count()


class Booking(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    # Relationships
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='bookings')
    guest = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings')
    
    # Booking Dates
    check_in = models.DateField()
    check_out = models.DateField()
    
    # Guest Details
    number_of_guests = models.PositiveIntegerField(
        validators=[MinValueValidator(1)]
    )
    guest_special_requests = models.TextField(blank=True)
    
    # Pricing
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    security_deposit_held = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Status and Timestamps
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    
    # Payment Information
    payment_intent_id = models.CharField(max_length=255, blank=True)  # For Stripe or similar
    payment_status = models.CharField(max_length=20, default='pending')
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['listing', 'check_in', 'check_out']),
            models.Index(fields=['guest', 'status']),
            models.Index(fields=['status']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(check_out__gt=models.F('check_in')),
                name='check_out_after_check_in'
            ),
        ]
    
    def __str__(self):
        return f"Booking #{self.id} - {self.listing.title} - {self.guest.username}"
    
    @property
    def duration(self):
        """Calculate booking duration in days"""
        return (self.check_out - self.check_in).days
    
    @property
    def is_active(self):
        """Check if booking is currently active"""
        today = timezone.now().date()
        return (self.status == 'active' and 
                self.check_in <= today <= self.check_out)
    
    @property
    def can_be_cancelled(self):
        """Check if booking can be cancelled"""
        return self.status in ['pending', 'confirmed'] and not self.is_active
    
    def calculate_total_price(self):
        """Calculate total price based on duration and listing prices"""
        duration = self.duration
        base_cost = duration * self.listing.base_price
        return base_cost + self.listing.cleaning_fee


class Review(models.Model):
    # Relationships
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='reviews')
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='review')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews_written')
    
    # Review Content
    rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    title = models.CharField(max_length=200)
    comment = models.TextField()
    
    # Response from host
    host_response = models.TextField(blank=True)
    host_response_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Moderation
    is_verified = models.BooleanField(default=False)  # Verified that author actually stayed
    is_public = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['listing', 'rating']),
            models.Index(fields=['author']),
            models.Index(fields=['is_public', 'is_verified']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['booking'],
                name='one_review_per_booking'
            ),
        ]
    
    def __str__(self):
        return f"Review for {self.listing.title} by {self.author.username} - {self.rating}/5"
    
    def save(self, *args, **kwargs):
        """Override save to ensure review is linked to the correct booking and listing"""
        if self.booking:
            self.listing = self.booking.listing
            self.author = self.booking.guest
        super().save(*args, **kwargs)


class ListingImage(models.Model):
    """Additional model for listing images"""
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='listing_images/')
    caption = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['order', 'created_at']
    
    def __str__(self):
        return f"Image for {self.listing.title}"