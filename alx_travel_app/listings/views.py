from django.shortcuts import render
from django.http import HttpResponse

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from django.db.models import Q
from .models import Listing, Booking, Review, ListingImage
from .serializers import (
    ListingSerializer, CreateListingSerializer, BookingSerializer,
    CreateBookingSerializer, ReviewSerializer, HostResponseSerializer,
    BookingStatusSerializer, ListingSearchSerializer, ListingImageSerializer
)

# Create your views here.
def listing_list(request):
    return HttpResponse("List of listings")

def listing_detail(request, pk):
    return HttpResponse(f"Details of listing {pk}")

class ListingViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['property_type', 'city', 'country', 'max_guests']
    search_fields = ['title', 'description', 'city', 'country']
    ordering_fields = ['base_price', 'created_at', 'average_rating']
    ordering = ['-created_at']
    
    def get_queryset(self):
        queryset = Listing.objects.filter(status='active')
        
        # Filter by availability if dates provided
        check_in = self.request.query_params.get('check_in')
        check_out = self.request.query_params.get('check_out')
        
        if check_in and check_out:
            # This is a simplified availability check
            unavailable_listings = Booking.objects.filter(
                Q(check_in__lt=check_out) & Q(check_out__gt=check_in),
                status__in=['confirmed', 'active']
            ).values_list('listing_id', flat=True)
            
            queryset = queryset.exclude(id__in=unavailable_listings)
        
        return queryset
    
    def get_serializer_class(self):
        if self.action == 'create':
            return CreateListingSerializer
        return ListingSerializer
    
    def perform_create(self, serializer):
        serializer.save(host=self.request.user)
    
    @action(detail=False, methods=['post'])
    def search(self, request):
        serializer = ListingSearchSerializer(data=request.data)
        if serializer.is_valid():
            queryset = Listing.objects.filter(status='active')
            
            # Apply filters based on search criteria
            data = serializer.validated_data
            
            if data.get('city'):
                queryset = queryset.filter(city__icontains=data['city'])
            
            if data.get('country'):
                queryset = queryset.filter(country__icontains=data['country'])
            
            if data.get('guests'):
                queryset = queryset.filter(max_guests__gte=data['guests'])
            
            if data.get('property_type'):
                queryset = queryset.filter(property_type=data['property_type'])
            
            if data.get('min_price'):
                queryset = queryset.filter(base_price__gte=data['min_price'])
            
            if data.get('max_price'):
                queryset = queryset.filter(base_price__lte=data['max_price'])
            
            # Availability check
            if data.get('check_in') and data.get('check_out'):
                unavailable_listings = Booking.objects.filter(
                    Q(check_in__lt=data['check_out']) & Q(check_out__gt=data['check_in']),
                    status__in=['confirmed', 'active']
                ).values_list('listing_id', flat=True)
                queryset = queryset.exclude(id__in=unavailable_listings)
            
            # Amenities filter
            if data.get('amenities'):
                amenity_filters = Q()
                for amenity in data['amenities']:
                    amenity_filters |= Q(**{amenity: True})
                queryset = queryset.filter(amenity_filters)
            
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = ListingSerializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            
            serializer = ListingSerializer(queryset, many=True)
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def bookings(self, request, pk=None):
        listing = self.get_object()
        bookings = listing.bookings.all()
        serializer = BookingSerializer(bookings, many=True)
        return Response(serializer.data)


class BookingViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Booking.objects.all()
        return Booking.objects.filter(guest=user)
    
    def get_serializer_class(self):
        if self.action == 'create':
            return CreateBookingSerializer
        elif self.action == 'update' and self.request.data.get('status'):
            return BookingStatusSerializer
        return BookingSerializer
    
    def perform_create(self, serializer):
        serializer.save(guest=self.request.user)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        booking = self.get_object()
        if booking.can_be_cancelled:
            booking.status = 'cancelled'
            booking.cancelled_at = timezone.now()
            booking.save()
            serializer = BookingSerializer(booking)
            return Response(serializer.data)
        return Response(
            {'error': 'This booking cannot be cancelled.'},
            status=status.HTTP_400_BAD_REQUEST
        )


class ReviewViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['listing', 'rating', 'is_verified']
    ordering_fields = ['rating', 'created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        return Review.objects.filter(is_public=True)
    
    def get_serializer_class(self):
        if self.action == 'update' and self.request.data.get('host_response'):
            return HostResponseSerializer
        return ReviewSerializer
    
    def perform_create(self, serializer):
        serializer.save(author=self.request.user)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def respond(self, request, pk=None):
        review = self.get_object()
        # Check if the current user is the host of the listing
        if review.listing.host != request.user:
            return Response(
                {'error': 'Only the host can respond to this review.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = HostResponseSerializer(review, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ListingImageViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ListingImageSerializer
    
    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return ListingImage.objects.all()
        return ListingImage.objects.filter(listing__host=user)
    
    def perform_create(self, serializer):
        listing = serializer.validated_data['listing']
        # Check if the current user is the host of the listing
        if listing.host != self.request.user:
            raise PermissionError("You can only add images to your own listings.")
        serializer.save()