#include "PluginEditor.h"

VstAiDemoAudioProcessorEditor::VstAiDemoAudioProcessorEditor(VstAiDemoAudioProcessor& p)
    : juce::AudioProcessorEditor(&p), processor(p)
{
    setSize(560, 240);
    
    // Set look and feel
    getLookAndFeel().setColour(juce::Slider::rotarySliderFillColourId, juce::Colour(0xFF7B68EE));
    getLookAndFeel().setColour(juce::Slider::rotarySliderOutlineColourId, juce::Colour(0xFF2F4F4F));
    getLookAndFeel().setColour(juce::Slider::thumbColourId, juce::Colour(0xFFFFFFFF));
    
    // Title label
    titleLabel.setText("Delay", juce::dontSendNotification);
    titleLabel.setFont(juce::Font(32.0f, juce::Font::bold));
    titleLabel.setColour(juce::Label::textColourId, juce::Colours::white);
    titleLabel.setJustificationType(juce::Justification::topLeft);
    addAndMakeVisible(titleLabel);
    
    // Delay Time Slider Setup
    delayTimeSlider.setSliderStyle(juce::Slider::RotaryVerticalDrag);
    delayTimeSlider.setTextBoxStyle(juce::Slider::NoTextBox, false, 0, 0);
    delayTimeSlider.setRange(1.0, 2000.0, 1.0);
    delayTimeSlider.setValue(500.0);
    addAndMakeVisible(delayTimeSlider);
    
    delayTimeAttachment = std::make_unique<juce::AudioProcessorValueTreeState::SliderAttachment>(
        processor.apvts, "delayTime", delayTimeSlider);
    
    // Delay Time label
    delayTimeLabel.setText("Time", juce::dontSendNotification);
    delayTimeLabel.setFont(juce::Font(14.0f));
    delayTimeLabel.setColour(juce::Label::textColourId, juce::Colours::white);
    delayTimeLabel.setJustificationType(juce::Justification::centred);
    addAndMakeVisible(delayTimeLabel);
    
    // Delay Time value label
    delayTimeValueLabel.setText("500 ms", juce::dontSendNotification);
    delayTimeValueLabel.setFont(juce::Font(12.0f));
    delayTimeValueLabel.setColour(juce::Label::textColourId, juce::Colours::white);
    delayTimeValueLabel.setColour(juce::Label::backgroundColourId, juce::Colour(0xFF1C1C1C));
    delayTimeValueLabel.setJustificationType(juce::Justification::centred);
    addAndMakeVisible(delayTimeValueLabel);
    
    // Mix Slider Setup
    mixSlider.setSliderStyle(juce::Slider::RotaryVerticalDrag);
    mixSlider.setTextBoxStyle(juce::Slider::NoTextBox, false, 0, 0);
    mixSlider.setRange(0.0, 100.0, 1.0);
    mixSlider.setValue(50.0);
    addAndMakeVisible(mixSlider);
    
    mixAttachment = std::make_unique<juce::AudioProcessorValueTreeState::SliderAttachment>(
        processor.apvts, "dryWetMix", mixSlider);
    
    // Mix label
    mixLabel.setText("Mix", juce::dontSendNotification);
    mixLabel.setFont(juce::Font(14.0f));
    mixLabel.setColour(juce::Label::textColourId, juce::Colours::white);
    mixLabel.setJustificationType(juce::Justification::centred);
    addAndMakeVisible(mixLabel);
    
    // Dry/Wet labels
    dryLabel.setText("Dry", juce::dontSendNotification);
    dryLabel.setFont(juce::Font(10.0f));
    dryLabel.setColour(juce::Label::textColourId, juce::Colours::lightgrey);
    dryLabel.setJustificationType(juce::Justification::centred);
    addAndMakeVisible(dryLabel);
    
    wetLabel.setText("Wet", juce::dontSendNotification);
    wetLabel.setFont(juce::Font(10.0f));
    wetLabel.setColour(juce::Label::textColourId, juce::Colours::lightgrey);
    wetLabel.setJustificationType(juce::Justification::centred);
    addAndMakeVisible(wetLabel);
    
    // Mix value label
    mixValueLabel.setText("50 %", juce::dontSendNotification);
    mixValueLabel.setFont(juce::Font(12.0f));
    mixValueLabel.setColour(juce::Label::textColourId, juce::Colours::white);
    mixValueLabel.setColour(juce::Label::backgroundColourId, juce::Colour(0xFF1C1C1C));
    mixValueLabel.setJustificationType(juce::Justification::centred);
    addAndMakeVisible(mixValueLabel);
    
    // Update value labels when sliders change
    delayTimeSlider.onValueChange = [this]()
    {
        delayTimeValueLabel.setText(juce::String(static_cast<int>(delayTimeSlider.getValue())) + " ms",
                                     juce::dontSendNotification);
    };
    
    mixSlider.onValueChange = [this]()
    {
        mixValueLabel.setText(juce::String(static_cast<int>(mixSlider.getValue())) + " %",
                              juce::dontSendNotification);
    };
}

void VstAiDemoAudioProcessorEditor::paint(juce::Graphics& g)
{
    // Dark gradient background
    juce::ColourGradient gradient(juce::Colour(0xFF0F0F0F), 0.0f, 0.0f,
                                   juce::Colour(0xFF1F1F1F), static_cast<float>(getWidth()), 
                                   static_cast<float>(getHeight()), false);
    g.setGradientFill(gradient);
    g.fillAll();
    
    // Vertical divider line between knobs
    g.setColour(juce::Colour(0xFF3F3F3F));
    g.drawVerticalLine(getWidth() / 2, 60.0f, static_cast<float>(getHeight()) - 20.0f);
}

void VstAiDemoAudioProcessorEditor::resized()
{
    int width = getWidth();
    int height = getHeight();
    
    // Title at top-left
    titleLabel.setBounds(20, 10, 150, 40);
    
    // Left knob area (Delay Time)
    int leftKnobX = width / 4 - 50;
    int knobY = 80;
    
    delayTimeSlider.setBounds(leftKnobX, knobY, 100, 100);
    delayTimeLabel.setBounds(leftKnobX, knobY + 100, 100, 20);
    delayTimeValueLabel.setBounds(leftKnobX + 10, height - 50, 80, 25);
    
    // Right knob area (Mix)
    int rightKnobX = (width / 4) * 3 - 50;
    
    mixSlider.setBounds(rightKnobX, knobY, 100, 100);
    mixLabel.setBounds(rightKnobX, knobY + 100, 100, 20);
    
    // Dry/Wet labels
    dryLabel.setBounds(rightKnobX - 40, knobY + 50, 35, 20);
    wetLabel.setBounds(rightKnobX + 100, knobY + 50, 35, 20);
    
    mixValueLabel.setBounds(rightKnobX + 10, height - 50, 80, 25);
}
